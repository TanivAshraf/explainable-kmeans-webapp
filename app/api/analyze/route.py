from http.server import BaseHTTPRequestHandler
import json
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from io import StringIO

NUM_CLUSTERS = 3

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data)
        csv_data = body.get('csv_data')

        if not csv_data:
            self.send_response(400) # Bad Request
            # ... (error handling) ...
            return

        try:
            df = pd.read_csv(StringIO(csv_data))
            
            # --- Perform Clustering ---
            df_features = df.drop('customer_id', axis=1)
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(df_features)
            kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10)
            df['cluster'] = kmeans.fit_predict(scaled_features)
            
            # --- Prepare Results for Explanation ---
            results = []
            for i in range(NUM_CLUSTERS):
                cluster_data = df[df['cluster'] == i]
                if len(cluster_data) > 0:
                    stats = cluster_data.drop(['customer_id', 'cluster'], axis=1).mean().to_dict()
                    results.append({
                        "cluster_id": i,
                        "num_customers": len(cluster_data),
                        "stats": stats
                    })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())

        except Exception as e:
            self.send_response(500)
            # ... (error handling) ...
        return
