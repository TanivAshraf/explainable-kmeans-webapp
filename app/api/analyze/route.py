from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import google.generativeai as genai
from io import StringIO

# --- CONFIGURATION ---
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
except KeyError:
    # This will be handled by the error response below
    pass

NUM_CLUSTERS = 3

# --- STAGE 1: K-MEANS CLUSTERING FUNCTION ---
def perform_clustering(df):
    df_features = df.drop('customer_id', axis=1)
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df_features)
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(scaled_features)
    return df

# --- STAGE 2: LLM EXPLANATION FUNCTION ---
def get_cluster_personas(clustered_df):
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    all_personas = []
    for i in range(NUM_CLUSTERS):
        cluster_data = clustered_df[clustered_df['cluster'] == i]
        if len(cluster_data) == 0:
            continue
        stats = cluster_data.drop(['customer_id', 'cluster'], axis=1).mean()
        prompt = f"""
        You are an expert data scientist and marketing analyst. A customer cluster has these average stats:
        - Age: {stats['age']:.1f}
        - Visits per Month: {stats['visits_per_month']:.1f}
        - Total Spent: ${stats['total_spent']:.2f}
        - Number of customers in this segment: {len(cluster_data)}

        Create a persona for this segment. Respond ONLY as a JSON object with keys: "persona_name", "description", "marketing_strategy".
        - "persona_name": A catchy name (e.g., 'Loyal High-Spenders').
        - "description": A 2-3 sentence summary.
        - "marketing_strategy": A single, actionable marketing tip.
        """
        response = model.generate_content(prompt)
        try:
            clean_response = response.text.replace('```json', '').replace('```', '').strip()
            persona = json.loads(clean_response)
            persona['cluster_id'] = i
            persona['cluster_stats'] = stats.to_dict() # Add raw stats for display
            all_personas.append(persona)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing JSON for cluster {i}: {e}")
    return all_personas

# --- VERCEL HANDLER ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data)
        csv_data = body.get('csv_data')

        if not csv_data:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'CSV data is required.'}).encode())
            return

        try:
            # Convert the CSV string into a Pandas DataFrame
            df = pd.read_csv(StringIO(csv_data))
            
            # Run the two-stage pipeline
            clustered_data = perform_clustering(df)
            personas = get_cluster_personas(clustered_data)
            
            # Send the successful response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(personas).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        return
