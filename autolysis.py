# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "openai",
#   "pandas",
#   "seaborn",
#   "matplotlib",
# ]
# ///

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import json

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv('AIPROXY_TOKEN')

# Check for API token
if not AIPROXY_TOKEN:
    print("Error: AIPROXY_TOKEN environment variable not set.")
    sys.exit(1)

# Headers for API requests
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AIPROXY_TOKEN}"
}

def read_csv_file(file_path):
    """Load the dataset from a CSV file."""
    try:
        df = pd.read_csv(file_path, encoding='latin1')
        print(f"Successfully loaded dataset: {file_path}")
        return df
    except Exception as error:
        print(f"Failed to load dataset: {error}")
        sys.exit(1)

def perform_analysis(df):
    """Perform a general analysis of the dataset."""
    analysis_results = {}
    try:
        analysis_results["shape"] = df.shape
        analysis_results["columns"] = df.dtypes.to_dict()
        analysis_results["missing_values"] = df.isnull().sum().to_dict()
        analysis_results["summary_stats"] = df.describe(include="all").to_dict()
        # Additional analysis for numeric columns only
        numeric_df = df.select_dtypes(include=["number"])
        if not numeric_df.empty:
            analysis_results["correlation_matrix"] = numeric_df.corr().to_dict()
            analysis_results["outliers"] = numeric_df[(numeric_df - numeric_df.mean()).abs() > 3 * numeric_df.std()].dropna().to_dict()
    except Exception as error:
        print(f"Error during analysis: {error}")
    return analysis_results

def create_visualizations(df, output_folder):
    """Create visualizations for the dataset."""
    os.makedirs(output_folder, exist_ok=True)
    charts = []
    try:
        numeric_df = df.select_dtypes(include=["number"])  # Define numeric_df here
        numeric_columns = numeric_df.columns[:3]  # Limit to 3 columns
        for col in numeric_columns:
            plt.figure(figsize=(6, 6))  # Set figure size to 512x512 pixels
            sns.histplot(df[col], kde=True, color="blue")
            plt.title(f"Distribution of {col}")
            plt.xlabel(col)
            plt.ylabel("Frequency")
            plt.legend([col])
            chart_file = os.path.join(output_folder, f"{col}_distribution.png")
            plt.savefig(chart_file, dpi=100)  # Save with dpi to control size
            plt.close()
            charts.append(chart_file)
        # Correlation heatmap
        if not numeric_df.empty:
            plt.figure(figsize=(6, 6))
            sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm')
            plt.title('Correlation Matrix')
            chart_file = os.path.join(output_folder, "correlation_matrix.png")
            plt.savefig(chart_file, dpi=100)
            plt.close()
            charts.append(chart_file)
    except Exception as error:
        print(f"Visualization error: {error}")
    return charts

def create_story(analysis, charts):
    """Generate a story summarizing the analysis using the LLM via AI Proxy."""
    try:
        prompt_text = (
            f"Dataset structure:\n"
            f"Shape: {analysis['shape']}\n"
            f"Columns: {analysis['columns']}\n"
            f"Missing Values: {analysis['missing_values']}\n"
            f"Summary Statistics: {analysis['summary_stats']}\n"
        )
        if "correlation_matrix" in analysis:
            prompt_text += f"Correlation Matrix: {analysis['correlation_matrix']}\n"
        if "outliers" in analysis:
            prompt_text += f"Outliers: {analysis['outliers']}\n"
        prompt_text += (
            f"\nVisualizations:\n"
            f"{', '.join(charts)}\n"
            f"Generate a summary of the dataset, key insights, and implications."
        )
        
        request_data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt_text}],
        }

        response = requests.post(API_URL, headers=headers, data=json.dumps(request_data))

        if response.status_code == 200:
            response_json = response.json()
            return response_json['choices'][0]['message']['content'].strip()
        else:
            print(f"API request failed: {response.status_code} - {response.text}")
            sys.exit(1)
    
    except Exception as error:
        print(f"Unexpected error: {error}")
        sys.exit(1)

def write_readme(story, charts, output_folder):
    """Save the story and visualizations to a README.md file."""
    try:
        readme_file = os.path.join(output_folder, "README.md")
        with open(readme_file, "w") as file:
            file.write("# Analysis Report\n\n")
            file.write(story + "\n\n")
            for chart in charts:
                relative_path = os.path.relpath(chart, output_folder)
                file.write(f"![Chart]({relative_path})\n\n")
        print(f"README.md created at {readme_file}")
    except Exception as error:
        print(f"Error writing README.md: {error}")

def main(file_path):
    """Main function to orchestrate the script."""
    output_folder = os.path.splitext(os.path.basename(file_path))[0]

    # Load data
    df = read_csv_file(file_path)

    # Analyze data
    analysis = perform_analysis(df)

    # Visualize data
    charts = create_visualizations(df, output_folder)

    # Generate story with LLM via AI Proxy
    story = create_story(analysis, charts)

    # Save README
    write_readme(story, charts, output_folder)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])