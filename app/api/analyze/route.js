import { GoogleGenerativeAI } from "@google/generative-ai";
import Papa from "papaparse";
import { kmeans } from "ml-kmeans";

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash-latest" });

const NUM_CLUSTERS = 3;

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function getPersonaForCluster(clusterData) {
  if (clusterData.length === 0) return null;

  const stats = clusterData.reduce((acc, row) => {
    acc.age += row.age;
    acc.visits_per_month += row.visits_per_month;
    acc.total_spent += row.total_spent;
    return acc;
  }, { age: 0, visits_per_month: 0, total_spent: 0 });

  stats.age /= clusterData.length;
  stats.visits_per_month /= clusterData.length;
  stats.total_spent /= clusterData.length;

  const prompt = `You are an expert data scientist and marketing analyst. A customer cluster has these average stats:
  - Age: ${stats.age.toFixed(1)}
  - Visits per Month: ${stats.visits_per_month.toFixed(1)}
  - Total Spent: $${stats.total_spent.toFixed(2)}
  - Number of customers in this segment: ${clusterData.length}

  Create a persona for this segment. Respond ONLY as a JSON object with keys: "persona_name", "description", "marketing_strategy".`;
  
  const result = await model.generateContent(prompt);
  const rawText = result.response.text();
  const startIndex = rawText.indexOf('{');
  const endIndex = rawText.lastIndexOf('}');
  const jsonString = rawText.substring(startIndex, endIndex + 1);
  return JSON.parse(jsonString);
}

export async function POST(request) {
  try {
    const body = await request.json();
    const csvData = body.csv_data;

    if (!csvData) {
      return new Response(JSON.stringify({ error: "CSV data is required." }), { status: 400 });
    }

    const parsed = Papa.parse(csvData, { header: true, dynamicTyping: true });
    const data = parsed.data.filter(row => row.customer_id != null && Object.keys(row).length > 1);

    if (data.length < NUM_CLUSTERS) {
        return new Response(JSON.stringify({ error: "Not enough data to form clusters. Please provide more rows." }), { status: 400 });
    }

    const vectors = data.map(row => [row.age, row.visits_per_month, row.total_spent]);
    
    const ans = kmeans(vectors, NUM_CLUSTERS, { initialization: 'kmeans++' });
    const assignments = ans.clusters;

    const clusters = Array.from({ length: NUM_CLUSTERS }, () => []);
    for (let i = 0; i < data.length; i++) {
        if(assignments[i] !== undefined) {
            clusters[assignments[i]].push(data[i]);
        }
    }
    
    const personaPromises = clusters.map(async (clusterData, index) => {
        if (clusterData.length > 0) {
            await delay(index * 1500); // Stagger API calls to avoid rate limits
            const persona = await getPersonaForCluster(clusterData);
            persona.cluster_id = index;
            return persona;
        }
        return null;
    });

    const personas = (await Promise.all(personaPromises)).filter(p => p !== null);
    
    return new Response(JSON.stringify(personas), { status: 200 });

  } catch (error) {
    console.error("Error in analysis API:", error);
    return new Response(JSON.stringify({ error: error.message || "An internal server error occurred." }), { status: 500 });
  }
}
