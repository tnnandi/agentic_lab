import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from geneformer import TranscriptomeTokenizer

# Set file paths
files_dir = '/Users/tnandi/Downloads/GSE255800_RAW'

# Read single-cell RNA-seq data files
def read_scRNAseq_data(files_dir):
    # Get list of files in the directory
    files = [f for f in os.listdir(files_dir) if f.startswith('GSM')]
    
    # Initialize empty lists to store data
    cell_barcodes = []
    gene_ids = []
    raw_counts = []
    
    for file in files:
        # Read matrix file (mtx format)
        mtx_file_path = os.path.join(files_dir, file + '_matrix.mtx')
        mtx_data = pd.read_csv(mtx_file_path, sep='\t', header=None, index_col=0)
        
        # Extract cell barcodes and gene IDs from the mtx data
        cell_barcodes.extend(mtx_data.index.values)
        gene_ids.extend(mtx_data.columns.values)
        
        # Read features file (tsv format)
        features_file_path = os.path.join(files_dir, file + '_features.tsv')
        features_data = pd.read_csv(features_file_path, sep='\t', header=None)
        
        # Append raw counts to the list
        raw_counts.append(features_data.iloc[:, 1].values)
    
    # Create a pandas DataFrame from the data
    scRNAseq_data = pd.DataFrame({
        'cell_barcodes': cell_barcodes,
        'gene_ids': gene_ids,
        'raw_counts': np.array(raw_counts).T
    })
    
    return scRNAseq_data

# Perform quality control and filtering on single-cell RNA-seq data
def qc_scRNAseq_data(scRNAseq_data):
    # Filter out cells with low number of genes expressed
    filtered_data = scRNAseq_data[scRNAseq_data['raw_counts'].sum(axis=1) > 100]
    
    # Remove genes that are not expressed in at least 10% of cells
    filtered_data = filtered_data.groupby('gene_ids')['raw_counts'].apply(lambda x: x[x>0].count()/len(filtered_data)).reset_index(name='expression_count')
    filtered_genes = filtered_data[filtered_data['expression_count'] > 0.1]['gene_ids']
    
    # Filter out cells that do not express any of the top 100 most variable genes
    top_100_var_genes = scRNAseq_data.groupby('gene_ids')['raw_counts'].apply(lambda x: x.std()).sort_values(ascending=False).head(100)['index'].values
    filtered_cells = filtered_data[filtered_data['cell_barcodes'].isin(filtered_data.loc[filtered_data['gene_ids'].isin(top_100_var_genes)]['cell_barcodes'])]
    
    return filtered_cells

# Tokenize single-cell RNA-seq data for Geneformer
def tokenize_scRNAseq_data(scRNAseq_data):
    # Create a TranscriptomeTokenizer object
    tk = TranscriptomeTokenizer()
    
    # Set up the token dictionary and gene median file
    tk.set_token_dict('/path/to/token/dict')
    tk.set_gene_median_file('/path/to/gene/median/file')
    
    # Tokenize the data
    tokenized_data = tk.tokenize(scRNAseq_data)
    
    return tokenized_data

# Main function to perform all tasks
def main():
    # Read single-cell RNA-seq data files
    scRNAseq_data = read_scRNAseq_data(files_dir)
    
    # Perform quality control and filtering on single-cell RNA-seq data
    filtered_cells = qc_scRNAseq_data(scRNAseq_data)
    
    # Tokenize single-cell RNA-seq data for Geneformer
    tokenized_data = tokenize_scRNAseq_data(filtered_cells)
    
    return tokenized_data

# Execute the main function
tokenized_data = main()

# Create plots to visualize the results
plt.hist(tokenized_data['raw_counts'], bins=100, alpha=0.5, label='Tokenized Data')
plt.title('Tokenized Single-Cell RNA-seq Data Histogram')
plt.xlabel('Raw Counts')
plt.ylabel('Frequency')
plt.legend()
plt.show()