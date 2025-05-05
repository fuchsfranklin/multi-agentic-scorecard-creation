# This script performs NLP analysis on clinical trial text data for cachexia studies.
# It extracts key attributes, classifies study phases, summarizes content, and discovers topics for downstream analysis or reporting.

import json
import re
from collections import Counter
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
import matplotlib.pyplot as plt
import os
from wordcloud import WordCloud
import numpy as np
from sklearn.manifold import TSNE
import seaborn as sns
import sys
# Add project root for llm_client import (disabled for cost reasons)
# script_dir_for_import = os.path.dirname(os.path.abspath(__file__))
# project_root_for_import = os.path.dirname(script_dir_for_import)
# sys.path.append(project_root_for_import)
# try:
#     from llm_client import LLMClient
# except ImportError:
#     print("Warning: llm_client not found, LLM extraction disabled.")
#     LLMClient = None
from llm_client import LLMClient, DailyRateLimitError  # re-enable LLM integration
# LLM functionality enabled; rate limits handled in llm_client.py

# Load the NLP JSON data (each entry contains the full text for a clinical trial)
def load_nlp_data(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Extract the study phase (e.g., Phase I, II, III, IV) from the text using regex
def extract_phases(text: str) -> str:
    match = re.search(r'(Phase\s*(I{1,3}|IV|1|2|3|4|Early Phase 1|Not Applicable))', text, re.IGNORECASE)
    return match.group(1) if match else None

# Extract the enrollment number (number of participants) from the text
def extract_enrollment(text: str) -> str:
    match = re.search(r'(enroll(?:ment)?\s*(of|=|:)\s*)(\d{2,5})', text, re.IGNORECASE)
    return match.group(3) if match else None

# Extract the primary endpoint (main outcome measured) from the text
def extract_primary_endpoint(text: str) -> str:
    match = re.search(r'primary endpoint:?\s*([^.\n]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

# Placeholder for Named-Entity Recognition (NER) for PICO elements (not implemented here)
def run_ner(texts: List[str]) -> List[Dict]:
    return [{} for _ in texts]

# Classify the study phase for each text (using regex extraction)
def classify_phase(texts: List[str]) -> List[str]:
    return [extract_phases(t) or 'Unknown' for t in texts]

# Discover main topics in the studies using topic modeling (NMF on TF-IDF features)
def topic_modeling(texts: List[str], n_topics=5):
    vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, stop_words='english')
    tfidf = vectorizer.fit_transform(texts)
    nmf = NMF(n_components=n_topics, random_state=1)
    W = nmf.fit_transform(tfidf)
    H = nmf.components_
    feature_names = vectorizer.get_feature_names_out()
    topics = []
    for topic_idx, topic in enumerate(H):
        top_words = [feature_names[i] for i in topic.argsort()[:-11:-1]]
        topics.append(top_words)
    return topics, W

# Create a publication-grade bar plot for phase distribution
def plot_phase_distribution(phase_counts):
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.figure(figsize=(10,5))
    # Group rare phases as 'Other' for clarity
    sorted_phases = phase_counts.most_common()
    phases, counts = zip(*sorted_phases)
    phases_adj, counts_adj = [], []
    other_count = 0
    for p, c in zip(phases, counts):
        if c < 5:
            other_count += c
        else:
            phases_adj.append(p)
            counts_adj.append(c)
    if other_count:
        phases_adj.append('Other')
        counts_adj.append(other_count)
    ax = sns.barplot(x=phases_adj, y=counts_adj, palette='Blues_d')
    ax.set_title('Study Phase Distribution (Regex-based)', fontsize=16, pad=16)
    ax.set_xlabel('Phase', fontsize=13, labelpad=10)
    ax.set_ylabel('Count', fontsize=13, labelpad=10)
    plt.xticks(rotation=30, ha='right', fontsize=11)
    plt.yticks(fontsize=11)
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    sns.despine()
    plt.savefig('phase_distribution.png', dpi=200)
    plt.show()

# Create a publication-grade plot for topic modeling results
def plot_topics(topics):
    import matplotlib.pyplot as plt
    import seaborn as sns  # <-- Add this import
    fig, ax = plt.subplots(figsize=(10, 4))
    topic_labels = [f"Topic {i+1}" for i in range(len(topics))]
    topic_words = ["\n".join(words[:8]) for words in topics]
    ax.bar(topic_labels, [1]*len(topics), color=sns.color_palette('Blues', len(topics)))
    for i, words in enumerate(topic_words):
        ax.text(i, 0.5, words, ha='center', va='center', fontsize=12)
    ax.set_ylim(0, 1.1)
    ax.set_yticks([])
    ax.set_title('Top Words per Topic (NMF Topic Modeling)', fontsize=16, pad=16)
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig('topic_modeling.png', dpi=200)
    plt.show()

# Save a summary table of results to a text file for easy review
def save_summary_table(phase_counts, topics):
    with open('nlp_analysis_summary.txt', 'w', encoding='utf-8') as f:
        f.write('Study Phase Distribution (Top 10):\n')
        for phase, count in phase_counts.most_common(10):
            f.write(f"  {phase}: {count}\n")
        f.write('\nTop Words per Topic:\n')
        for i, topic_words in enumerate(topics):
            f.write(f"  Topic {i+1}: {', '.join(topic_words)}\n")

def normalize_phase_label(label):
    # Improved normalization for varied formats
    if not label:
        return 'Unknown'
    l = re.sub(r'\s+', '', label.lower())  # remove whitespace
    l = re.sub(r'[\/\-\(\)]', '', l)
    if 'earlyphase1' in l or 'phase0' in l:
        return 'Early Phase 1/0'
    if l in ('phasei','phase1'):
        return 'Phase I'
    if l in ('phaseii','phase2'):
        return 'Phase II'
    if l in ('phaseiii','phase3'):
        return 'Phase III'
    if l in ('phaseiv','phase4'):
        return 'Phase IV'
    if 'notapplicable' in l or l=='na':
        return 'Not Applicable'
    return 'Unknown'

# New: extract phase via LLM for a small sample (disabled)
# if LLMClient:
#     def extract_phase_llm(text: str, llm: LLMClient) -> str:
#         prompt = f"Extract study phase from text..."
#         try:
#             resp = llm.generate(prompt).strip()
#             norm = normalize_phase_label(resp)
#             return norm
#         except Exception:
#             return 'Unknown'

def advanced_topic_analysis(texts, n_topics, W, topics, outdir):
    # Assign each study to its most probable topic based on NMF weights
    topic_assignments = np.argmax(W, axis=1)
    topic_counts = Counter(topic_assignments)
    # Save topic prevalence (how many studies per topic)
    with open(os.path.join(outdir, 'topic_prevalence.json'), 'w', encoding='utf-8') as f:
        json.dump({f'Topic {k+1}': v for k, v in topic_counts.items()}, f, indent=2)

    # Generate and save wordclouds for each topic
    for i in range(n_topics):
        idxs = np.where(topic_assignments == i)[0]
        if len(idxs) == 0:
            print(f"Warning: No studies assigned to Topic {i+1}, skipping wordcloud.")
            continue
        topic_text = ' '.join([texts[j] for j in idxs])
        try:
            wc = WordCloud(width=800, height=400, background_color='white').generate(topic_text)
            wc.to_file(os.path.join(outdir, f'topic_{i+1}_wordcloud.png'))
        except ValueError as e:
            print(f"Warning: Could not generate wordcloud for Topic {i+1}: {e}")

    # N-gram analysis: find common two-word phrases (bigrams)
    from sklearn.feature_extraction.text import CountVectorizer
    bigram_vectorizer = CountVectorizer(ngram_range=(2,2), stop_words='english', min_df=2)
    try:
        bigram_matrix = bigram_vectorizer.fit_transform(texts)
        bigram_freq = np.asarray(bigram_matrix.sum(axis=0)).flatten()
        bigram_terms = bigram_vectorizer.get_feature_names_out()
        bigram_counts = sorted(zip(bigram_terms, bigram_freq), key=lambda x: -x[1])[:20]
        with open(os.path.join(outdir, 'top_bigrams.txt'), 'w', encoding='utf-8') as f:
            for term, freq in bigram_counts:
                f.write(f'{term}: {int(freq)}\n') # Ensure freq is int
    except ValueError as e:
        print(f"Warning: Could not perform bigram analysis: {e}")

    # Study length statistics: plot distribution of text length
    lengths = [len(t.split()) for t in texts]
    plt.figure(figsize=(8,4))
    sns.histplot(lengths, bins=30, color='purple')
    plt.title('Distribution of Study Text Length (words)')
    plt.xlabel('Number of Words')
    plt.ylabel('Number of Studies')
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, 'study_length_distribution.png'), dpi=200)
    plt.close() # Close plot to prevent display

    # t-SNE visualization: plot studies in 2D based on topic similarity
    try:
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, W.shape[0]-1)) # Adjust perplexity
        tsne_embeds = tsne.fit_transform(W)
        plt.figure(figsize=(8,6))
        palette = sns.color_palette('tab10', n_topics)
        for i in range(n_topics):
            plt.scatter(tsne_embeds[topic_assignments==i,0], tsne_embeds[topic_assignments==i,1], label=f'Topic {i+1}', alpha=0.6, s=20, color=palette[i])
        plt.legend()
        plt.title('t-SNE Visualization of Study Topics')
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, 'tsne_topics.png'), dpi=200)
        plt.close() # Close plot
    except ValueError as e:
        print(f"Warning: Could not perform t-SNE visualization: {e}")

    # Save representative studies: show a snippet of the most representative study for each topic
    with open(os.path.join(outdir, 'topic_representative_studies.txt'), 'w', encoding='utf-8') as f:
        for i in range(n_topics):
            idxs = np.where(topic_assignments == i)[0]
            top_idx = idxs[np.argmax(W[idxs,i])] if len(idxs) > 0 else None
            f.write(f'--- Topic {i+1} ---\n')
            if top_idx is not None:
                f.write(texts[top_idx][:500].replace('\n',' ') + '...\n\n')
            else:
                f.write('No studies assigned.\n\n')

def extract_pico_llm(text: str, llm: LLMClient) -> dict:
    """Call LLM to extract PICO elements as JSON."""
    prompt = f"""
You are a clinical research assistant. Extract the following from the trial text below.
Return a JSON object with keys: population, intervention, comparator, outcomes.

Trial Text:
""" + text[:1500] + """
"""
    response = llm.generate(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "invalid JSON", "raw": response}


def infer_phase_llm(text: str, llm: LLMClient) -> str:
    """Call LLM to infer study phase for texts labeled 'Unknown'."""
    prompt = f"""
Given the following clinical trial description, infer the most likely study phase.
Possible values: Early Phase 1/0, Phase I, Phase II, Phase III, Phase IV, Not Applicable.
Return just the phase label.

{text[:1500]}
"""
    resp = llm.generate(prompt).strip()
    return normalize_phase_label(resp)

# Main workflow: load data, extract attributes, classify, summarize, model topics, and visualize
def main():
    # Define output directory relative to script location or project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    outdir = os.path.join(project_root, 'data', 'nlp')
    os.makedirs(outdir, exist_ok=True)

    # Define input file path
    input_file = os.path.join(outdir, 'cachexia_studies_fetched_nlp_texts.json')

    # Load the full text for each clinical trial
    data = load_nlp_data(input_file)
    texts = [d['nlp_text'] for d in data if d.get('nlp_text')]
    if not texts:
        print("Error: No text data found in input file.")
        return

    # Attribute Extraction: pull out phase, enrollment, and primary endpoint
    phases = [extract_phases(t) for t in texts]
    enrollments = [extract_enrollment(t) for t in texts]
    primary_endpoints = [extract_primary_endpoint(t) for t in texts]

    # Classification: assign a phase label to each study and normalize
    phase_classes = classify_phase(texts)
    norm_phases = [normalize_phase_label(p) for p in phase_classes] # Use classified phases
    norm_phase_counts = Counter(norm_phases)
    print('Normalized Phase Distribution:', norm_phase_counts)

    # LLM-based phase extraction sample (disabled)
    # if LLMClient:
    #     sample_results = []
    #     for i, t in enumerate(texts[:10]):
    #         sample_results.append({
    #             'nctId': nct_ids[i],
    #             'regex': norm_regex_phases[i],
    #             'llm': extract_phase_llm(t, llm)
    #         })
    #     with open(os.path.join(outdir,'llm_phase_sample.json'),'w',encoding='utf-8') as f:
    #         json.dump(sample_results,f,indent=2)

    # Summarization: create a short summary for each study (first 300 chars)
    summaries = [t[:300] + '...' if len(t) > 300 else t for t in texts]

    # Topic Modeling: discover main themes across all studies
    n_topics = 5
    try:
        topics, W = topic_modeling(texts, n_topics=n_topics)
        print('\nTop words per topic:')
        for i, topic_words in enumerate(topics):
            print(f"Topic {i+1}: {', '.join(topic_words)}")
    except ValueError as e:
        print(f"Error during topic modeling: {e}. Not enough documents or features?")
        return

    # Save normalized phase distribution counts
    with open(os.path.join(outdir, 'phase_distribution.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(norm_phase_counts), f, indent=2)

    # Plot phase distribution (publication grade)
    plt.figure(figsize=(10,5))
    sorted_phases = norm_phase_counts.most_common()
    phases_plot, counts_plot = zip(*sorted_phases)
    ax = sns.barplot(x=list(phases_plot), y=list(counts_plot), palette='Blues_d')
    ax.set_title('Study Phase Distribution (Normalized)', fontsize=16, pad=16)
    ax.set_xlabel('Phase', fontsize=13, labelpad=10)
    ax.set_ylabel('Count', fontsize=13, labelpad=10)
    plt.xticks(rotation=30, ha='right', fontsize=11)
    plt.yticks(fontsize=11)
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    sns.despine()
    plt.savefig(os.path.join(outdir, 'phase_distribution.png'), dpi=200)
    plt.close() # Close plot

    # Plot topic modeling results (publication grade)
    plot_topics(topics)
    # Note: plot_topics already saves the figure, no need to save again here
    plt.close() # Close plot

    # Advanced topic/statistical analysis
    advanced_topic_analysis(texts, n_topics, W, topics, outdir)

    # Save summary table (using normalized counts)
    save_summary_table(norm_phase_counts, topics)
    # Correct path for summary table - use replace to overwrite if exists
    try:
        os.replace('nlp_analysis_summary.txt', os.path.join(outdir, 'nlp_analysis_summary.txt'))
    except OSError as e:
        print(f"Error moving summary file: {e}")

    # Save extracted attributes for further analysis
    with open(os.path.join(outdir, 'nlp_extracted_attributes.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'phases': norm_phases, # Save normalized phases
            'enrollments': enrollments,
            'primary_endpoints': primary_endpoints,
            'summaries': summaries
        }, f, indent=2)

    # Incremental LLM-based PICO extraction
    if LLMClient:
        pico_file = os.path.join(outdir, 'pico_extractions.json')
        try:
            pico_data = json.load(open(pico_file))
        except (FileNotFoundError, json.JSONDecodeError):
            pico_data = []
        llm = LLMClient()
        batch_size = 5
        start = len(pico_data)
        for idx in range(start, min(start + batch_size, len(texts))):
            try:
                pico = extract_pico_llm(texts[idx], llm)
            except DailyRateLimitError:
                print("Reached daily LLM limit during PICO extraction, stopping batch.")
                break
            pico_data.append({'nctId': data[idx].get('nctId'), 'pico': pico})
        with open(pico_file, 'w', encoding='utf-8') as f:
            json.dump(pico_data, f, indent=2)

    # Incremental LLM-based phase inference for 'Unknown'
    if LLMClient:
        phase_inf_file = os.path.join(outdir, 'phase_inference.json')
        try:
            phase_inf = json.load(open(phase_inf_file))
        except (FileNotFoundError, json.JSONDecodeError):
            phase_inf = []
        llm = LLMClient()
        unknown_idxs = [i for i,p in enumerate(norm_phases) if p=='Unknown']
        start_inf = len(phase_inf)
        for j in unknown_idxs[start_inf:start_inf+batch_size]:
            try:
                inferred = infer_phase_llm(texts[j], llm)
            except DailyRateLimitError:
                print("Reached daily LLM limit during phase inference, stopping batch.")
                break
            phase_inf.append({'nctId': data[j].get('nctId'), 'inferred_phase': inferred})
        with open(phase_inf_file, 'w', encoding='utf-8') as f:
            json.dump(phase_inf, f, indent=2)

if __name__ == '__main__':
    main()
