from http.server import BaseHTTPRequestHandler
import json
import os
import google.generativeai as genai

try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
except KeyError:
    pass

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)
            
            stats = body.get('stats')
            cluster_id = body.get('cluster_id')
            num_customers = body.get('num_customers')

            if not stats:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Cluster stats are required.'}).encode())
                return

            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            prompt = f"""
            You are an expert data scientist and marketing analyst. A customer cluster has these average stats:
            - Age: {stats.get('age', 0):.1f}
            - Visits per Month: {stats.get('visits_per_month', 0):.1f}
            - Total Spent: ${stats.get('total_spent', 0):.2f}
            - Number of customers in this segment: {num_customers}

            Create a persona for this segment. Respond ONLY as a JSON object with keys: "persona_name", "description", "marketing_strategy".
            """
            response = model.generate_content(prompt)
            clean_response = response.text.replace('```json', '').replace('```', '').strip()
            persona = json.loads(clean_response)
            persona['cluster_id'] = cluster_id
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(persona).encode())
            
        except Exception as e:
            # --- THE FIX: Ensure we always write a JSON error body ---
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f"An error occurred in the explanation API: {str(e)}"}).encode())
            # --- END FIX ---
        return
