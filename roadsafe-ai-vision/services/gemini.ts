
import { GoogleGenAI, Type } from "@google/genai";

const SYSTEM_PROMPT = `You are RoadSense, an expert road hazard detection system analyzing dashcam footage from Indian roads. You have deep familiarity with Indian road conditions — unmarked speed breakers, potholes patched with gravel, informal cuts in highway dividers, festival-related obstructions, and other hazards unique to Indian driving. 

Detection Instructions:
- Scan every frame for hazards in the vehicle's path or immediate surroundings.
- For each hazard, estimate WHEN in the clip it first becomes visible (as seconds from chunk start).
- Estimate WHERE in the frame the hazard is located (as approximate bounding box coordinates between 0 and 1).
- Assess severity based on potential impact to a vehicle traveling at normal speed (1-5 scale).
- Be CONSERVATIVE with false positives. A shadow is not a pothole.
- Do not consider deliberate camera movement by the user as an issue.

Hazard Categories:
- POTHOLE: Visible road surface damage, craters, broken tarmac.
- SPEED_BREAKER: Marked or unmarked speed bumps, raised surfaces across the road.
- PEDESTRIAN_ZONE: Active pedestrian crossings, school zones, market areas with foot traffic.
- OVERHEAD_OBSTRUCTION: Low-hanging branches, cables, signage intruding into vehicle clearance.
- ROAD_WORK: Active construction, repair zones, exposed manholes, barricades.
- SHARP_CURVE: Blind turns with the driver still visible.
- SURFACE_CHANGE: Transition from paved to unpaved, gravel patches, waterlogged sections.`;

export async function analyzeRoadSafetyVideo(videoBase64: string, mimeType: string): Promise<string> {
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
  
  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: {
        parts: [
          {
            inlineData: {
              mimeType: mimeType,
              data: videoBase64,
            },
          },
          { text: "Analyze this dashcam footage segment and detect all road hazards visible from the driver's perspective. Source: GoPro dashcam, forward-facing. Location: Indian roads. Chunk: Segment 1 of the drive (0s to end)." }
        ],
      },
      config: {
        systemInstruction: SYSTEM_PROMPT,
        temperature: 0.1,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              hazard_id: { type: Type.STRING },
              category: { 
                type: Type.STRING,
                enum: ["POTHOLE", "SPEED_BREAKER", "PEDESTRIAN_ZONE", "OVERHEAD_OBSTRUCTION", "ROAD_WORK", "SHARP_CURVE", "SURFACE_CHANGE"]
              },
              severity: { type: Type.INTEGER, description: "Severity scale 1 (LOW) to 5 (CRITICAL)" },
              timestamp_offset_sec: { type: Type.NUMBER },
              description: { type: Type.STRING },
              bounding_box: {
                type: Type.OBJECT,
                properties: {
                  x_min: { type: Type.NUMBER },
                  y_min: { type: Type.NUMBER },
                  x_max: { type: Type.NUMBER },
                  y_max: { type: Type.NUMBER }
                },
                required: ["x_min", "y_min", "x_max", "y_max"]
              },
              driver_action: { type: Type.STRING },
              confidence: { type: Type.NUMBER }
            },
            required: ["hazard_id", "category", "severity", "timestamp_offset_sec", "description", "bounding_box", "driver_action", "confidence"]
          }
        }
      },
    });

    return response.text;
  } catch (error) {
    console.error("Gemini Analysis Error:", error);
    throw new Error("Failed to analyze video. Ensure the file is valid and the API is accessible.");
  }
}
