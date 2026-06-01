Act as a Senior AI Product Architect and Video Tech Specialist. I am building a SaaS application that converts long-form videos (like podcasts, webinars, and streams) into short-form content (TikTok, Reels, YouTube Shorts). 

Currently, my app has a basic setup where it centralizes subtitles and extracts clips. However, I want to upgrade and refine its architecture to compete directly with premium paid tools (like Opus Clip, Munch, and Klap) instead of free manual editors like CapCut.

Please design a comprehensive product requirement framework covering the following core AI-driven features:

1. AI Virality Curation (Auto-Clipping):
- How should the backend analyze long-form transcripts to detect high-engagement hooks, emotional peaks, or complete conversational contexts?
- Provide a scoring logic framework to rank the virality potential of each generated clip.

2. Auto-Reframe & Face Tracking (16:9 to 9:16):
- What is the best technical approach (e.g., computer vision/YOLO models) to detect the speaker’s face and smoothly re-center the video layout dynamically without manual keyframes?

3. Kinetic B-Roll & Visual Enhancements:
- How can the system automatically inject contextually relevant B-roll footage, screen overlays, or zoom-in effects during transitions or specific keywords?

4. Smart Captions with Auto-Emoji & Keyword Highlighting:
- Define the data structure (JSON) required to map words to milliseconds.
- How can we implement an AI layer that automatically highlights impactful words (e.g., changing text color to neon green or yellow) and inserts matching emojis (e.g., placing a 💰 emoji next to the word "money") based on semantic meaning?

5. Batch Processing & Pipeline Scalability:
- Provide a high-level cloud architecture recommendation (e.g., AWS, GCP, or serverless video rendering pipelines) to process a 1-hour video and generate 10+ styled clips simultaneously under 10 minutes.

Deliver this as a highly detailed, actionable technical roadmap. Focus on universal development terminology, clean JSON schemas where applicable, and specific AI models or APIs I should leverage to build these features.
