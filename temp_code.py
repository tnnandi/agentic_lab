import pandas as pd
from scipy import io
import scanpy as sc
from geneformer import Geneformer
import os

def load_data(files_dir):
    data = []
    for file in os.listdir(files_dir):
        if file.endswith('.mtx'):
            mtx_file = os.path.join(files_dir, file)
            df = pd.read_csv(mtx_file, delimiter='\t', index_col=0)
            data.append(df)
    return pd.concat(data, axis=1)

def quality_control(data):
    sc.pp.filter_cells(data, min_genes=200)
    sc.pp.filter_genes(data, min_cells=10)
    data = data[data.obs['n_counts'] > 1000]
    return data

def gene_expression_analysis(data):
    geneformer_model = Geneformer()
    gene_expr = geneformer_model.predict(data)
    return gene_expr

def identify_responsible_genes(gene_expr, data):
    # Perform differential expression analysis using scanpy
    sc.tl.pca(data)
    sc.tl.lle(data)
    sc.tl.diffmap(data)
    
    # Use Geneformer model to identify genes responsible for low-dose radiation induced changes
    responsible_genes = geneformer_model.identify_responsible_genes(gene_expr, data)
    return responsible_genes

files_dir = '/Users/tnandi/Downloads/GSE255800_extracted'
data = load_data(files_dir)
print("Data Loaded")
data = quality_control(data)
print("Quality Control Done")
gene_expr = gene_expression_analysis(data)
print("Gene Expression Analysis Done")
responsible_genes = identify_responsible_genes(gene_expr, data)
print(responsible_genes)