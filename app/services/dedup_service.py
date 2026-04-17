import os
import pandas as pd
from typing import Dict, Any, List, Set, Tuple
from rapidfuzz import fuzz
import re
import numpy as np
import google.generativeai as genai
import time
from app.utils.file_manager import write_csv
from app.utils.common import safe_json_parse

# Configure Gemini
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
model = None
if api_key:
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-2.5-flash')

def _normalize_question(text: str) -> str:
    """
    Normalizes question text for fuzzy comparison.
    Lowercases, removes punctuation, and collapses spaces.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_embeddings_batched(texts: List[str], batch_size: int = 100) -> np.ndarray:
    """
    Fetches embeddings for a list of texts using Gemini API in batches.
    Returns a numpy array of shape (N, D).
    """
    embeddings = []
    total = len(texts)
    
    print(f"Fetching embeddings for {total} questions...")
    
    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        try:
            # Replace empty strings to avoid API errors
            safe_batch = [t if t and t.strip() else "empty_string_placeholder" for t in batch]
            
            # Using text-embedding-004
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=safe_batch,
                task_type="semantic_similarity"
            )
            
            if 'embedding' in result:
                embeddings.extend(result['embedding'])
            else:
                print(f"Warning: No embeddings returned for batch {i}")
                embeddings.extend([[0.0]*768] * len(batch))
                
        except Exception as e:
            print(f"Error fetching embeddings for batch {i}: {e}")
            # Simple retry
            time.sleep(2)
            try:
                safe_batch = [t if t and t.strip() else "empty_string_placeholder" for t in batch]
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=safe_batch,
                    task_type="semantic_similarity"
                )
                embeddings.extend(result['embedding'])
            except Exception as e2:
                print(f"Retry failed: {e2}")
                embeddings.extend([[0.0]*768] * len(batch))
                
    return np.array(embeddings)

def resolve_clusters_with_gemini(clusters: List[Dict[str, Any]]) -> List[int]:
    """
    Sends batches of clusters to Gemini to identify semantic duplicates.
    Returns a list of indices (IDs) to REMOVE.
    """
    ids_to_remove = []
    
    # Process clusters in batches to fit in context window
    # Each cluster has: {'indices': [i, j, k], 'questions': ["q1", "q2", "q3"]}
    
    BATCH_SIZE = 10  # Number of clusters to send at once
    
    for i in range(0, len(clusters), BATCH_SIZE):
        batch_clusters = clusters[i : i + BATCH_SIZE]
        
        prompt_lines = [
            "You are an expert editor. Below are groups of questions. Inside each group, the questions are potentially duplicates (rephrased versions).",
            "For EACH group:",
            "1. Analyze the questions.",
            "2. Identify if they are semantic duplicates (same meaning/answer).",
            "3. If they are duplicates, keep the BEST phrased one and mark the others for removal.",
            "4. If they are distinct questions, do NOT mark any for removal.",
            "Return a JSON object with a single key 'remove_indices' which is a flat list of ALL integer IDs to remove across all groups.",
            "\nGroups:"
        ]
        
        for idx, cluster in enumerate(batch_clusters):
            prompt_lines.append(f"\nGroup {idx + 1}:")
            for q_idx, q_text in zip(cluster['indices'], cluster['questions']):
                prompt_lines.append(f"ID {q_idx}: {q_text}")
        
        prompt = "\n".join(prompt_lines)
        
        try:
            response = model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            batch_remove = result.get("remove_indices", [])
            if isinstance(batch_remove, list):
                ids_to_remove.extend(batch_remove)
                
        except Exception as e:
            print(f"Error resolving clusters batch {i}: {e}")
            # Fallback: In case of error, if they were very similar (>0.95), we might want to auto-remove?
            # For now, safe fallback is to KEEP them to avoid data loss.
            pass
            
    return ids_to_remove

def remove_semantic_duplicates(df: pd.DataFrame, filename_prefix: str, save_output: bool = True) -> Dict[str, Any]:
    """
    Removes semantic/near-duplicate questions using a Hybrid approach:
    1. Exact deduplication (Pandas)
    2. Global Embedding Clustering (Gemini Embeddings)
    3. LLM Verification for ambiguous cases (Gemini Pro)
    """
    # Detect question column
    question_col = None
    for col in df.columns:
        if "question" in col.lower():
            question_col = col
            break

    if not question_col:
        for col in df.columns:
            if df[col].dtype == object and df[col].astype(str).str.len().mean() > 10:
                question_col = col
                break

    if not question_col:
        raise ValueError("Could not identify a 'Question' column in the CSV.")

    original_count = len(df)
    
    # 1. Exact Deduplication
    print("Step 1: Exact Deduplication...")
    # Use a temporary column for normalization to catch "  What is X? " vs "What is X?"
    df['temp_norm_q'] = df[question_col].astype(str).str.strip().str.lower()
    df_clean = df.drop_duplicates(subset=['temp_norm_q'], keep='first').copy()
    df_clean = df_clean.drop(columns=['temp_norm_q'])
    
    print(f"Exact dedup removed {original_count - len(df_clean)} rows.")
    
    # Reset index for matrix operations, but keep original index mapping if needed?
    # Simpler to reset and work with new indices
    df_clean = df_clean.reset_index(drop=True)
    questions = df_clean[question_col].fillna("").astype(str).tolist()
    
    ids_to_remove = set()
    
    # 2. Embedding Deduplication
    if api_key and len(questions) > 0:
        try:
            print("Step 2: Global Embedding Clustering...")
            emb_matrix = get_embeddings_batched(questions)
            
            if len(emb_matrix) == len(questions):
                # Normalize
                norms = np.linalg.norm(emb_matrix, axis=1)
                norms[norms == 0] = 1
                normalized_emb = emb_matrix / norms[:, np.newaxis]
                
                # Similarity Matrix
                similarity_matrix = np.dot(normalized_emb, normalized_emb.T)
                
                # Thresholds
                # > 0.96: Auto-remove (High confidence duplicate)
                # > 0.80: Verify with LLM (Ambiguous/Rephrased)
                AUTO_THRESHOLD = 0.96
                VERIFY_THRESHOLD = 0.80 # Lowered to catch widely rephrased duplicates
                
                processed_indices = set()
                clusters_to_verify = []
                
                total_rows = len(questions)
                
                for i in range(total_rows):
                    if i in processed_indices:
                        continue
                    
                    if i in ids_to_remove:
                        continue
                        
                    processed_indices.add(i)
                    
                    # Find neighbors
                    # We only look at j > i to avoid double counting
                    sim_scores = similarity_matrix[i]
                    
                    # Find all indices where sim > VERIFY_THRESHOLD (excluding self)
                    # We look at ALL indices to form a complete cluster, then filter processed
                    candidates = np.where(sim_scores > VERIFY_THRESHOLD)[0]
                    candidates = [c for c in candidates if c != i and c not in ids_to_remove]
                    
                    if not candidates:
                        continue
                        
                    # Separate into Auto-Remove and Verify
                    cluster_indices = [i]
                    
                    for cand in candidates:
                        score = sim_scores[cand]
                        if score > AUTO_THRESHOLD:
                            # Auto-remove
                            ids_to_remove.add(cand)
                            processed_indices.add(cand)
                        else:
                            # Add to cluster for verification
                            cluster_indices.append(cand)
                            processed_indices.add(cand)
                            
                    # If we have multiple candidates for verification
                    if len(cluster_indices) > 1:
                        clusters_to_verify.append({
                            "indices": cluster_indices,
                            "questions": [questions[idx] for idx in cluster_indices]
                        })
                        
                print(f"Found {len(ids_to_remove)} auto-duplicates and {len(clusters_to_verify)} clusters to verify.")
                
                # 3. LLM Verification
                if clusters_to_verify:
                    print(f"Step 3: Verifying {len(clusters_to_verify)} clusters with Gemini...")
                    verified_remove_ids = resolve_clusters_with_gemini(clusters_to_verify)
                    print(f"Gemini identified {len(verified_remove_ids)} additional duplicates.")
                    ids_to_remove.update(verified_remove_ids)
                    
            else:
                print("Embedding mismatch.")
                
        except Exception as e:
            print(f"Embedding deduplication failed: {e}")
            
    # Remove rows
    final_keep_indices = [i for i in range(len(df_clean)) if i not in ids_to_remove]
    final_df = df_clean.iloc[final_keep_indices].copy()
    
    final_filename = ""
    if save_output:
        base_filename = f"{filename_prefix}_cleaned"
        write_csv(base_filename, final_df)
        final_filename = f"{base_filename}.csv"
    
    return {
        "filename": final_filename,
        "original_count": original_count,
        "cleaned_count": len(final_df),
        "removed_count": original_count - len(final_df),
        "df": final_df
    }
