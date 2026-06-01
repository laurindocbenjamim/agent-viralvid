# ViralVid 2.0 - Premium AI Video Clipper Architecture Roadmap

## Executive Summary

Transform ViralVid from a basic subtitle+clip extractor into an AI-powered short-form content engine that competes with Opus Clip, Munch, and Klap. This roadmap addresses 5 core feature areas with production-ready technical specifications.

---

## Current State Assessment

### What Exists
- FastAPI modular monolith with LangChain-Groq LLM integration
- Groq Whisper STT for word-level transcription
- MoviePy-based 9:16 cropping with Pillow subtitle rendering
- Redis/SQLite dual persistence layer
- Background task orchestration

### Critical Gaps to Address
1. **Mock transcript in LLM analysis** - Currently analyzing fake content, not real video
2. **No face tracking** - Static center crop only
3. **No B-roll injection** - Only basic subtitles
4. **Limited caption intelligence** - Basic keyword highlighting (length > 4 chars)
5. **Single-threaded processing** - No batch capabilities

---

## Feature 1: AI Virality Curation (Auto-Clipping)

### 1.1 Real Transcript Analysis Pipeline

**Current Problem**: `pipeline.py` uses a hardcoded Portuguese string instead of actual video transcript.

**Solution**: Implement two-phase analysis:

```
Phase 1: Full Video Transcription (Groq Whisper)
    ↓
Phase 2: LLM Virality Analysis (on real transcript)
    ↓
Phase 3: Clip Extraction with Context Windows
```

### 1.2 Enhanced LLM Prompt Engineering

Replace the current simple prompt with a structured virality analysis system prompt:

```python
VIRALITY_ANALYSIS_SYSTEM_PROMPT = """
You are an expert short-form video curator analyzing a podcast/webinar transcript.

For each potential viral clip, identify:

1. HOOK QUALITY (0-100):
   - Does it start with a controversial statement, question, or surprising fact?
   - Would someone stop scrolling within 0.5 seconds?
   - Example hooks: "This one mistake costs...", "Nobody talks about...", "The truth is..."

2. EMOTIONAL INTENSITY (0-100):
   - Detect emotional peaks: excitement, anger, surprise, inspiration
   - Look for: exclamation marks, emphatic language, personal stories
   - Score higher for authentic emotional moments

3. CONTEXT COMPLETENESS (0-100):
   - Does the clip make sense standalone?
   - Are there complete thought units?
   - Score 0 if clip requires external context

4. SHAREABILITY (0-100):
   - Would viewers tag friends?
   - Is there a "wait, I need to send this" moment?
   - Does it provoke discussion/debate?

5. PATTERN INTERRUPT (0-100):
   - Does the content break from expected flow?
   - Are there unexpected twists or revelations?
   - Sudden topic changes or "plot twists"

OUTPUT SCHEMA:
{
  "clips": [
    {
      "start_seconds": float,
      "end_seconds": float,
      "hook_text": "First 3-5 words that grab attention",
      "title": "Clickbait-worthy title",
      "scores": {
        "hook": int,
        "emotion": int,
        "context": int,
        "shareability": int,
        "pattern_interrupt": int
      },
      "virality_score": "calculated weighted average",
      "emotional_arc": ["calm", "peak", "resolution"],
      "target_emotion": "inspiration|humor|outrage|curiosity",
      "best_hashtags": ["#hashtag1", "#hashtag2"]
    }
  ]
}
"""
```

### 1.3 Virality Scoring Algorithm

```python
def calculate_virality_score(scores: dict) -> float:
    """
    Weighted scoring formula optimized for platform algorithms.
    
    Weights based on TikTok/Reels engagement research:
    - Hook is king (35% weight) - First 0.5s determines 65% of watch time
    - Emotional intensity drives shares (25% weight)
    - Shareability amplifies reach (20% weight)
    - Context ensures comprehension (15% weight)
    - Pattern interrupt stops the scroll (5% weight)
    """
    weights = {
        "hook": 0.35,
        "emotion": 0.25,
        "shareability": 0.20,
        "context": 0.15,
        "pattern_interrupt": 0.05
    }
    
    weighted_sum = sum(scores[k] * weights[k] for k in weights)
    
    # Apply threshold penalties
    if scores["context"] < 30:
        weighted_sum *= 0.5  # Penalize incomplete context heavily
    
    if scores["hook"] < 40:
        weighted_sum *= 0.7  # Penalize weak hooks
    
    return round(weighted_sum, 2)


def rank_clips(clips: list) -> list:
    """Rank clips with diversity factor to avoid similar content."""
    # Sort by virality score
    sorted_clips = sorted(clips, key=lambda x: x["virality_score"], reverse=True)
    
    # Apply diversity filter - no two adjacent clips within 30 seconds
    selected = []
    last_end = -30
    
    for clip in sorted_clips:
        if clip["start_seconds"] - last_end >= 30:
            selected.append(clip)
            last_end = clip["end_seconds"]
            if len(selected) >= 10:  # Cap at 10 clips
                break
    
    return selected
```

### 1.4 Transcript Window Strategy

For long videos (1+ hour), implement sliding window analysis:

```python
TRANSCRIPT_WINDOW_SIZE = 300  # 5 minutes
TRANSCRIPT_WINDOW_OVERLAP = 30  # 30 seconds overlap

def analyze_long_transcript(full_transcript: str, duration: float) -> list:
    """Process long transcripts in overlapping windows."""
    all_clips = []
    
    for start in range(0, int(duration), TRANSCRIPT_WINDOW_SIZE - TRANSCRIPT_WINDOW_OVERLAP):
        end = min(start + TRANSCRIPT_WINDOW_SIZE, duration)
        window_text = extract_transcript_window(full_transcript, start, end)
        
        # Analyze this window
        window_clips = llm_analyze_virality(window_text)
        
        # Adjust timestamps to global timeline
        for clip in window_clips:
            clip["start_seconds"] += start
            clip["end_seconds"] += start
        
        all_clips.extend(window_clips)
    
    # Global deduplication and ranking
    return deduplicate_and_rank(all_clips)
```

---

## Feature 2: Auto-Reframe & Face Tracking (16:9 → 9:16)

### 2.1 Technical Approach: YOLO + ByteTrack

**Why YOLOv8 + ByteTrack over alternatives:**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| YOLOv8 + ByteTrack | Fast (30+ FPS), accurate, lightweight | Requires GPU for real-time | **RECOMMENDED** |
| MediaPipe Face Detection | Google-backed, good for faces only | No body tracking, less robust | Backup option |
| OpenCV Haar Cascades | No dependencies | Slow, outdated, poor accuracy | Avoid |
| AWS Rekognition | No ML infra needed | Latency, cost at scale, vendor lock | For serverless fallback |

### 2.2 Face Detection Pipeline

```python
from ultralytics import YOLO
from byte_tracker import ByteTrack

class FaceTracker:
    def __init__(self):
        # YOLOv8 nano model - 3.2M params, runs on CPU
        self.face_model = YOLO('yolov8n-face.pt')  # Fine-tuned for faces
        self.person_model = YOLO('yolov8n.pt')  # General person detection
        self.tracker = ByteTrack(track_thresh=0.5, track_buffer=30)
        
        # Smoothing parameters
        self.smoothing_window = 10  # frames
        self.position_history = {}
    
    def process_video(self, video_path: str) -> list:
        """Extract face positions for every frame."""
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        positions = []
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect faces
            results = self.face_model(frame, verbose=False)
            
            # If no face, try full person detection
            if len(results[0].boxes) == 0:
                results = self.person_model(frame, verbose=False)
            
            # Get bounding boxes
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
            # Track with ByteTrack
            detections = [
                ([x1, y1, x2-x1, y2-y1], conf)
                for (x1, y1, x2, y2), conf in zip(boxes, confidences)
            ]
            
            tracked = self.tracker.update(detections)
            
            # Extract primary speaker (highest confidence or largest)
            primary = self.get_primary_speaker(tracked, frame.shape)
            
            # Smooth position over window
            smoothed = self.smooth_position(frame_idx, primary)
            
            positions.append({
                "frame": frame_idx,
                "timestamp": frame_idx / fps,
                "x_center": smoothed[0],
                "y_center": smoothed[1],
                "bbox_width": smoothed[2],
                "bbox_height": smoothed[3],
                "confidence": smoothed[4]
            })
            
            frame_idx += 1
        
        cap.release()
        return positions
    
    def get_primary_speaker(self, tracked_detections, frame_shape):
        """Select the primary speaker based on size and position."""
        if not tracked_detections:
            # Default to center
            h, w = frame_shape[:2]
            return (w//2, h//2, 100, 100, 0.0)
        
        # Pick largest face (likely closest to camera)
        best = max(tracked_detections, 
                   key=lambda d: d[1][2] * d[1][3])  # area
        
        x, y, w, h = best[1]
        return (x + w//2, y + h//2, w, h, best[2])
    
    def smooth_position(self, frame_idx, position):
        """Apply exponential moving average for smooth movement."""
        alpha = 0.3  # Smoothing factor
        
        if frame_idx not in self.position_history:
            self.position_history[frame_idx] = position
            return position
        
        prev = self.position_history.get(frame_idx - 1, position)
        smoothed = tuple(
            alpha * p + (1 - alpha) * pr 
            for p, pr in zip(position, prev)
        )
        
        self.position_history[frame_idx] = smoothed
        return smoothed
```

### 2.3 Dynamic Reframing with MoviePy

```python
from moviepy.editor import VideoFileClip

class DynamicReframer:
    def __init__(self, target_width=1080, target_height=1920):
        self.target_width = target_width
        self.target_height = target_height
        self.target_aspect = target_width / target_height  # 0.5625
    
    def reframe_video(self, video_path: str, face_positions: list) -> str:
        """Reframe horizontal video to vertical with face tracking."""
        import cv2
        import numpy as np
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        src_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        src_aspect = src_width / src_height
        
        # Calculate crop dimensions
        crop_height = src_height
        crop_width = int(crop_height * self.target_aspect)
        
        output_frames = []
        
        for frame_idx in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Get smoothed face position for this frame
            pos = self.get_position_for_frame(face_positions, frame_idx)
            
            # Calculate crop center (clamp to frame bounds)
            x_center = int(np.clip(pos["x_center"], 
                                   crop_width/2, 
                                   src_width - crop_width/2))
            y_center = int(np.clip(pos["y_center"],
                                  crop_height/2,
                                  src_height - crop_height/2))
            
            # Extract crop region
            x1 = x_center - crop_width // 2
            y1 = y_center - crop_height // 2
            x2 = x1 + crop_width
            y2 = y1 + crop_height
            
            cropped = frame[y1:y2, x1:x2]
            
            # Resize to target dimensions
            resized = cv2.resize(cropped, (self.target_width, self.target_height))
            output_frames.append(resized)
        
        cap.release()
        
        # Write output
        output_path = f"{video_path}_reframed.mp4"
        self.write_video(output_frames, output_path, fps)
        
        return output_path
    
    def get_position_for_frame(self, positions, frame_idx):
        """Interpolate position between keyframes."""
        # Find surrounding keyframes
        for i, pos in enumerate(positions):
            if pos["frame"] >= frame_idx:
                if i == 0:
                    return pos
                prev = positions[i-1]
                # Linear interpolation
                t = (frame_idx - prev["frame"]) / (pos["frame"] - prev["frame"])
                return {
                    "x_center": prev["x_center"] + t * (pos["x_center"] - prev["x_center"]),
                    "y_center": prev["y_center"] + t * (pos["y_center"] - prev["y_center"]),
                }
        return positions[-1] if positions else {"x_center": 960, "y_center": 540}
```

### 2.4 Crop Mode Enhancements

Update `video_editor.py` to support new modes:

```python
CROP_MODES = {
    "center": "Static center crop (current)",
    "smart_track": "YOLO face tracking + ByteTrack (NEW)",
    "multi_speaker": "Split-screen for conversations (NEW)",
    "panoramic": "Animated pan across wide shots (NEW)",
    "hybrid": "Face tracking with center fallback (NEW)"
}
```

---

## Feature 3: Kinetic B-Roll & Visual Enhancements

### 3.1 B-Roll Content Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    B-ROLL INJECTION POINTS                   │
├─────────────────────────────────────────────────────────────┤
│  1. Transitions (topic changes)                              │
│  2. Keyword triggers (specific words in transcript)          │
│  3. Emotional peaks (high excitement moments)                │
│  4. Lists/Numbers (when speaker enumerates)                  │
│  5. Comparisons (this vs that)                               │
│  6. Visual breaks (long talking head segments > 30s)         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Keyword-to-BRoll Mapping System

```python
KEYWORD_BRROLL_DATABASE = {
    # Business/Finance
    "money": {"clip": "cash_counting.mp4", "overlay": "💰", "zoom": 1.2},
    "revenue": {"clip": "chart_upward.mp4", "overlay": "📈", "zoom": 1.1},
    "invest": {"clip": "stock_market.mp4", "overlay": "💼", "zoom": 1.0},
    
    # Technology
    "ai": {"clip": "neural_network.mp4", "overlay": "🤖", "zoom": 1.3},
    "code": {"clip": "programming_screen.mp4", "overlay": "💻", "zoom": 1.2},
    "data": {"clip": "data_flow.mp4", "overlay": "📊", "zoom": 1.1},
    
    # Emotions
    "love": {"clip": "heart_animation.mp4", "overlay": "❤️", "zoom": 1.4},
    "amazing": {"clip": "fireworks.mp4", "overlay": "✨", "zoom": 1.5},
    "fail": {"clip": "explosion.mp4", "overlay": "💥", "zoom": 1.3},
    
    # Actions
    "subscribe": {"clip": "notification_bell.mp4", "overlay": "🔔", "zoom": 1.2},
    "share": {"clip": "viral_spread.mp4", "overlay": "↗️", "zoom": 1.1},
    "link": {"clip": "chain_connect.mp4", "overlay": "🔗", "zoom": 1.0}
}

class BRollEngine:
    def __init__(self, broll_library_path: str):
        self.library = self.load_library(broll_library_path)
        self.keyword_index = self.build_keyword_index()
    
    def analyze_transcript_for_broll(self, transcript: list) -> list:
        """Identify moments where B-roll should be injected."""
        injection_points = []
        
        for i, segment in enumerate(transcript):
            text = segment["text"].lower()
            words = text.split()
            
            # Check for keyword matches
            for keyword, broll_config in self.keyword_index.items():
                if keyword in text:
                    injection_points.append({
                        "timestamp": segment["start"],
                        "duration": segment["end"] - segment["start"],
                        "keyword": keyword,
                        "broll_clip": broll_config["clip"],
                        "overlay_emoji": broll_config["overlay"],
                        "zoom_factor": broll_config["zoom"],
                        "context_window": self.get_context_window(transcript, i, 3)
                    })
            
            # Check for transition patterns
            if self.is_topic_transition(transcript, i):
                injection_points.append({
                    "timestamp": segment["start"],
                    "duration": 2.0,
                    "type": "transition",
                    "broll_clip": self.get_transition_clip(text),
                    "overlay_emoji": "🎬",
                    "zoom_factor": 1.0
                })
        
        return self.deduplicate_injections(injection_points)
    
    def is_topic_transition(self, transcript: list, index: int) -> bool:
        """Detect when speaker changes topics."""
        transition_phrases = [
            "but here's the thing", "let me tell you", "speaking of",
            "now let's talk about", "moving on", "next up", "the key is",
            "what's really important", "here's what most people miss"
        ]
        
        if index == 0:
            return False
        
        current_text = transcript[index]["text"].lower()
        return any(phrase in current_text for phrase in transition_phrases)
```

### 3.3 Zoom Effect System

```python
class KineticZoom:
    """Dynamic zoom effects synced to audio/video content."""
    
    ZOOM_PRESETS = {
        "emphasis": {
            "start_scale": 1.0,
            "end_scale": 1.4,
            "duration": 0.5,
            "easing": "ease_in_out",
            "target": "face"  # Zoom toward detected face
        },
        "dramatic_reveal": {
            "start_scale": 1.0,
            "end_scale": 2.0,
            "duration": 1.0,
            "easing": "ease_out",
            "target": "center"
        },
        "subtle_breath": {
            "start_scale": 1.0,
            "end_scale": 1.05,
            "duration": 2.0,
            "easing": "sine_in_out",
            "target": "face"
        },
        "whip_zoom": {
            "start_scale": 1.0,
            "end_scale": 1.6,
            "duration": 0.2,
            "easing": "ease_in",
            "target": "keyword_position"
        }
    }
    
    def apply_zoom_effect(self, video_clip, effect_type: str, 
                          trigger_timestamp: float) -> VideoClip:
        """Apply zoom effect at specific timestamp."""
        preset = self.ZOOM_PRESETS[effect_type]
        
        def zoom_function(t):
            if t < trigger_timestamp:
                return 1.0
            
            elapsed = t - trigger_timestamp
            progress = min(elapsed / preset["duration"], 1.0)
            
            # Apply easing
            eased_progress = self.apply_easing(progress, preset["easing"])
            
            # Interpolate scale
            scale = (preset["start_scale"] + 
                    (preset["end_scale"] - preset["start_scale"]) * eased_progress)
            
            return scale
        
        return video_clip.resize(zoom_function)
```

### 3.4 Overlay System

```python
class OverlayEngine:
    """Text overlays, animations, and visual effects."""
    
    OVERLAY_TEMPLATES = {
        "stat_reveal": {
            "type": "text",
            "animation": "slide_up",
            "duration": 3.0,
            "style": {
                "font": "Montserrat-Bold",
                "size": 72,
                "color": "#FFFFFF",
                "stroke": {"color": "#000000", "width": 4},
                "shadow": True
            }
        },
        "emoji_burst": {
            "type": "emoji",
            "animation": "burst_from_center",
            "count": 5,
            "duration": 1.5,
            "emojis": ["🔥", "💰", "🚀", "💡", "⭐"]
        },
        "progress_bar": {
            "type": "graphic",
            "animation": "fill_left_to_right",
            "position": "bottom",
            "height": 8,
            "color_gradient": ["#00f5d4", "#00bbf9", "#9b5de5"]
        },
        "speaker_name": {
            "type": "lower_third",
            "animation": "slide_in_left",
            "duration": 4.0,
            "style": {
                "name_font": "Poppins-Bold",
                "title_font": "Poppins-Regular",
                "background": "rgba(0,0,0,0.7)",
                "accent_color": "#00f5d4"
            }
        }
    }
```

---

## Feature 4: Smart Captions with Auto-Emoji & Keyword Highlighting

### 4.1 Enhanced Caption Data Structure

```json
{
  "metadata": {
    "video_id": "task-uuid-123",
    "total_duration_ms": 3600000,
    "language": "pt-BR",
    "caption_style": "cyberpunk",
    "words_per_second": 2.5
  },
  "caption_segments": [
    {
      "id": "seg_001",
      "start_ms": 0,
      "end_ms": 4500,
      "position": "center",
      "words": [
        {
          "word": "Olá",
          "start_ms": 0,
          "end_ms": 320,
          "confidence": 0.98,
          "is_highlighted": false,
          "highlight_color": null,
          "animation": "none"
        },
        {
          "word": "pessoal",
          "start_ms": 320,
          "end_ms": 680,
          "confidence": 0.97,
          "is_highlighted": false,
          "highlight_color": null,
          "animation": "none"
        },
        {
          "word": "dinheiro",
          "start_ms": 1200,
          "end_ms": 1650,
          "confidence": 0.95,
          "is_highlighted": true,
          "highlight_color": "#00FF00",
          "highlight_style": "glow",
          "animation": "pulse",
          "emoji_trigger": {
            "emoji": "💰",
            "position": "right",
            "animation": "bounce_in",
            "scale": 1.5
          }
        },
        {
          "word": "incrível",
          "start_ms": 1650,
          "end_ms": 2100,
          "confidence": 0.94,
          "is_highlighted": true,
          "highlight_color": "#FFFF00",
          "highlight_style": "neon",
          "animation": "typewriter",
          "emoji_trigger": null
        }
      ],
      "background_overlay": {
        "type": "gradient",
        "color": "rgba(0,0,0,0.6)",
        "blur": 10
      }
    }
  ],
  "word_annotations": [
    {
      "word": "dinheiro",
      "semantic_category": "financial",
      "importance_score": 0.92,
      "suggested_emojis": ["💰", "💵", "🤑", "💲"],
      "highlight_colors": ["#00FF00", "#39FF14", "#7FFF00"]
    },
    {
      "word": "incrível",
      "semantic_category": "emotion_positive",
      "importance_score": 0.88,
      "suggested_emojis": ["🤯", "✨", "🔥", "💯"],
      "highlight_colors": ["#FFFF00", "#FFD700", "#FFA500"]
    }
  ],
  "animation_keyframes": [
    {
      "timestamp_ms": 0,
      "scale": 0.8,
      "opacity": 0,
      "y_offset": 20
    },
    {
      "timestamp_ms": 100,
      "scale": 1.0,
      "opacity": 1,
      "y_offset": 0
    }
  ]
}
```

### 4.2 AI Keyword Highlighting System

```python
from langchain_groq import ChatGroq
from pydantic import BaseModel
from typing import List, Optional

class WordAnnotation(BaseModel):
    word: str
    start_ms: int
    end_ms: int
    is_highlighted: bool
    highlight_color: Optional[str] = None
    highlight_style: Optional[str] = None  # glow, neon, outline, pulse
    animation: Optional[str] = None  # none, typewriter, bounce, pulse
    emoji_trigger: Optional[dict] = None
    semantic_category: Optional[str] = None
    importance_score: float = 0.0

class CaptionHighlighter:
    def __init__(self):
        self.llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct")
        
        # Semantic categories for emoji mapping
        self.SEMANTIC_EMOJI_MAP = {
            "financial": ["💰", "💵", "🤑", "💲", "🏦"],
            "technology": ["🤖", "💻", "🚀", "⚡", "🔧"],
            "emotion_positive": ["❤️", "😍", "🥰", "✨", "🔥"],
            "emotion_negative": ["😤", "💔", "😢", "⚠️", "🚨"],
            "food": ["🍕", "🍔", "🍟", "🌮", "🍣"],
            "nature": ["🌊", "🌳", "☀️", "🌙", "⭐"],
            "success": ["🏆", "🥇", "🎯", "✅", "👑"],
            "warning": ["⚠️", "🚨", "⛔", "❌", "👀"],
            "idea": ["💡", "🧠", "🤔", "💭", "📝"],
            "time": ["⏰", "⏱️", "📅", "⏳", "🕐"]
        }
        
        # Highlight colors by category
        self.CATEGORY_COLORS = {
            "financial": "#00FF00",      # Neon green
            "technology": "#00BFFF",     # Deep sky blue
            "emotion_positive": "#FFD700", # Gold
            "emotion_negative": "#FF4500", # Orange red
            "success": "#FFD700",         # Gold
            "warning": "#FF6347",         # Tomato
            "idea": "#FFA500"            # Orange
        }
    
    def analyze_words_for_highlighting(self, words: list) -> list:
        """Use LLM to determine which words to highlight and why."""
        
        prompt = f"""
        Analyze these words from a video transcript and identify which ones 
        should be visually highlighted for maximum viewer engagement.
        
        Words: {[w["word"] for w in words]}
        
        For each word, determine:
        1. Should it be highlighted? (true/false)
        2. Semantic category (financial, technology, emotion, etc.)
        3. Importance score (0-1)
        4. Suggested emoji (if applicable)
        5. Highlight color recommendation
        
        Rules:
        - Highlight 15-25% of words (not too many, not too few)
        - Focus on: nouns, adjectives, verbs of action, numbers
        - Skip: articles, prepositions, common verbs (is, are, have)
        - Financial words get green, tech gets blue, emotions get yellow
        - Emojis should be contextually relevant and not overused
        
        Return JSON array of annotations.
        """
        
        response = self.llm.invoke(prompt)
        annotations = self.parse_llm_response(response.content)
        
        return annotations
    
    def assign_emoji(self, word: str, semantic_category: str) -> Optional[str]:
        """Select the best emoji for a word based on semantics."""
        
        if semantic_category in self.SEMANTIC_EMOJI_MAP:
            emojis = self.SEMANTIC_EMOJI_MAP[semantic_category]
            # Could add LLM call here for better selection
            return emojis[0]  # Default to first
        
        return None
    
    def generate_animation_keyframes(self, word: str, 
                                     highlight_type: str) -> list:
        """Generate animation keyframes for highlighted words."""
        
        ANIMATIONS = {
            "pulse": [
                {"scale": 1.0, "time_offset_ms": 0},
                {"scale": 1.3, "time_offset_ms": 150},
                {"scale": 1.0, "time_offset_ms": 300}
            ],
            "bounce": [
                {"y_offset": 0, "time_offset_ms": 0},
                {"y_offset": -20, "time_offset_ms": 100},
                {"y_offset": 0, "time_offset_ms": 200},
                {"y_offset": -10, "time_offset_ms": 250},
                {"y_offset": 0, "time_offset_ms": 300}
            ],
            "typewriter": [
                {"opacity": 0, "time_offset_ms": 0},
                {"opacity": 0.5, "time_offset_ms": 50},
                {"opacity": 1, "time_offset_ms": 100}
            ],
            "glow": [
                {"glow_intensity": 0, "time_offset_ms": 0},
                {"glow_intensity": 1, "time_offset_ms": 200},
                {"glow_intensity": 0.5, "time_offset_ms": 400}
            ]
        }
        
        return ANIMATIONS.get(highlight_type, [])
```

### 4.3 Caption Renderer (Pillow Enhanced)

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class EnhancedCaptionRenderer:
    def __init__(self):
        self.fonts = {
            "bold": ImageFont.truetype("Montserrat-Bold.ttf", 80),
            "regular": ImageFont.truetype("Montserrat-Regular.ttf", 60),
            "emoji": ImageFont.truetype("NotoColorEmoji.ttf", 100)
        }
    
    def render_caption_segment(self, segment: dict, frame_size: tuple) -> Image:
        """Render a caption segment with all effects."""
        width, height = frame_size
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate total width for centering
        total_width = self.calculate_segment_width(segment)
        x_start = (width - total_width) // 2
        
        current_x = x_start
        base_y = self.get_position_y(segment["position"], height)
        
        for word_data in segment["words"]:
            word = word_data["word"]
            
            if word_data["is_highlighted"]:
                # Render highlighted word with effects
                self.render_highlighted_word(
                    draw, word, current_x, base_y,
                    color=word_data["highlight_color"],
                    style=word_data.get("highlight_style", "glow"),
                    animation=word_data.get("animation")
                )
                
                # Render emoji if present
                if word_data.get("emoji_trigger"):
                    emoji_x = current_x + self.get_word_width(word) + 10
                    self.render_emoji(
                        draw, word_data["emoji_trigger"]["emoji"],
                        emoji_x, base_y - 20
                    )
            else:
                # Render normal word
                draw.text(
                    (current_x, base_y),
                    word,
                    font=self.fonts["bold"],
                    fill="white",
                    stroke_width=3,
                    stroke_fill="black"
                )
            
            current_x += self.get_word_width(word) + 20
        
        return img
    
    def render_highlighted_word(self, draw, word, x, y, color, style, animation):
        """Render word with highlight effects."""
        
        if style == "neon":
            # Neon glow effect
            for offset in range(6, 0, -2):
                glow_color = self.adjust_alpha(color, 50)
                draw.text(
                    (x, y), word,
                    font=self.fonts["bold"],
                    fill=glow_color,
                    stroke_width=offset
                )
            
            # Core text
            draw.text(
                (x, y), word,
                font=self.fonts["bold"],
                fill=color,
                stroke_width=2,
                stroke_fill="black"
            )
        
        elif style == "glow":
            # Soft glow effect
            glow_img = Image.new('RGBA', draw.im.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_img)
            glow_draw.text((x, y), word, font=self.fonts["bold"], fill=color)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=8))
            draw.im.paste(glow_img, (0, 0), glow_img)
            
            # Core text on top
            draw.text(
                (x, y), word,
                font=self.fonts["bold"],
                fill="white",
                stroke_width=3,
                stroke_fill="black"
            )
        
        elif style == "outline":
            # Animated outline effect
            for i in range(3):
                draw.text(
                    (x-i, y), word,
                    font=self.fonts["bold"],
                    fill=None,
                    stroke_width=2,
                    stroke_fill=color
                )
            
            draw.text(
                (x, y), word,
                font=self.fonts["bold"],
                fill="white"
            )
```

---

## Feature 5: Batch Processing & Pipeline Scalability

### 5.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   Frontend   │────▶│   API GW     │────▶│   FastAPI    │     │
│  │  (React/Next)│     │  (CloudFront)│     │   Workers    │     │
│  └──────────────┘     └──────────────┘     └──────┬───────┘     │
│                                                     │             │
│                          ┌─────────────────────────┼──────┐     │
│                          │                          │      │     │
│                          ▼                          ▼      │     │
│                   ┌─────────────┐            ┌────────────┐│     │
│                   │    SQS     │            │   Redis    ││     │
│                   │   Queue    │            │  (Cache)   ││     │
│                   └──────┬─────┘            └────────────┘│     │
│                          │                                │     │
│         ┌────────────────┼────────────────┐              │     │
│         ▼                ▼                ▼              │     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │     │
│  │  Worker 1   │  │  Worker 2   │  │  Worker N   │     │     │
│  │  (GPU)      │  │  (GPU)      │  │  (GPU)      │     │     │
│  │  - Download │  │  - Download │  │  - Download │     │     │
│  │  - STT      │  │  - STT      │  │  - STT      │     │     │
│  │  - FaceTrack│  │  - FaceTrack│  │  - FaceTrack│     │     │
│  │  - Render   │  │  - Render   │  │  - Render   │     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │     │
│         │                │                │              │     │
│         └────────────────┼────────────────┘              │     │
│                          ▼                                │     │
│                   ┌─────────────┐                        │     │
│                   │  S3 Bucket  │◀───────────────────────┘     │
│                   │  (Outputs)  │                                │
│                   └─────────────┘                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 AWS Cloud Architecture

```yaml
# cloudformation-template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ViralVid 2.0 - AI Video Processing Pipeline'

Resources:
  # Compute
  ProcessingQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: viralvid-processing
      VisibilityTimeout: 900  # 15 minutes for long videos
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue.Arn
        maxReceiveCount: 3
  
  DeadLetterQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: viralvid-dead-letter
  
  # GPU Workers (EC2 G4 instances)
  WorkerAutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      MinSize: 0
      MaxSize: 10
      DesiredCapacity: 2
      LaunchTemplate:
        LaunchTemplateName: viralvid-worker
        Version: !GetAtt WorkerLaunchTemplate.LatestVersionNumber
  
  WorkerLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateData:
        ImageId: ami-xxx  # Deep Learning AMI
        InstanceType: g4dn.xlarge  # T4 GPU, 4 vCPU, 16GB RAM
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum install -y docker
            service docker start
            docker pull viralvid/worker:latest
            docker run -d viralvid/worker
            
        # Estimated performance: 10 min per 1hr video
  
  # Storage
  OutputBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: viralvid-outputs
      LifecycleConfiguration:
        Rules:
          - Id: AutoExpire
            Status: Enabled
            ExpirationInDays: 7  # Auto-cleanup
  
  CacheCluster:
    Type: AWS::ElastiCache::CacheCluster
    Properties:
      CacheNodeType: cache.t3.medium
      Engine: redis
      NumCacheNodes: 1
  
  # Database
  TaskDatabase:
    Type: AWS::RDS::DBInstance
    Properties:
      Engine: postgres
      DBInstanceClass: db.t3.micro
      AllocatedStorage: 20
```

### 5.3 Worker Implementation

```python
# worker.py - Runs on GPU instances
import asyncio
from celery import Celery
from fastapi import FastAPI

app = Celery('viralvid_worker', broker='sqs://')

class VideoProcessingWorker:
    def __init__(self):
        self.face_tracker = FaceTracker()
        self.reframer = DynamicReframer()
        self.broll_engine = BRollEngine("/opt/broll_library")
        self.caption_renderer = EnhancedCaptionRenderer()
    
    @app.task(bind=True, max_retries=3, time_limit=900)
    def process_video(self, task_id: str, video_url: str, options: dict):
        """Main processing pipeline for a single video."""
        
        try:
            # Phase 1: Download
            self.update_status(task_id, "downloading", 10)
            video_path = self.download_video(video_url)
            
            # Phase 2: Full Transcript
            self.update_status(task_id, "transcribing", 20)
            transcript = self.transcribe_full_video(video_path)
            
            # Phase 3: Virality Analysis
            self.update_status(task_id, "analyzing", 30)
            viral_moments = self.analyze_virality(transcript)
            
            # Phase 4: Face Tracking (on full video)
            self.update_status(task_id, "tracking", 40)
            face_positions = self.face_tracker.process_video(video_path)
            
            # Phase 5: Process Each Clip
            clips = []
            for i, moment in enumerate(viral_moments):
                progress = 50 + (i / len(viral_moments)) * 40
                
                self.update_status(task_id, f"rendering_clip_{i+1}", progress)
                
                clip_result = self.process_single_clip(
                    video_path=video_path,
                    moment=moment,
                    face_positions=face_positions,
                    options=options,
                    clip_index=i
                )
                clips.append(clip_result)
            
            # Phase 6: Finalize
            self.update_status(task_id, "completed", 100, clips=clips)
            
            return {"status": "success", "clips": clips}
        
        except Exception as e:
            self.update_status(task_id, "failed", error=str(e))
            raise
    
    def process_single_clip(self, video_path, moment, face_positions, 
                           options, clip_index):
        """Process a single clip with all effects."""
        
        # Extract clip segment
        clip_video = self.extract_segment(
            video_path, 
            moment["start_seconds"],
            moment["end_seconds"]
        )
        
        # Apply reframing
        if options.get("crop_mode") == "smart_track":
            clip_faces = self.filter_positions(
                face_positions, 
                moment["start_seconds"],
                moment["end_seconds"]
            )
            clip_video = self.reframer.reframe_video(clip_video, clip_faces)
        else:
            clip_video = self.static_crop(clip_video, options["crop_mode"])
        
        # Analyze transcript for B-roll
        clip_transcript = self.extract_transcript_segment(
            moment["start_seconds"],
            moment["end_seconds"]
        )
        broll_injections = self.broll_engine.analyze_transcript_for_broll(
            clip_transcript
        )
        
        # Inject B-roll
        if broll_injections:
            clip_video = self.inject_broll(clip_video, broll_injections)
        
        # Generate captions
        caption_data = self.generate_captions(clip_transcript)
        
        # Apply captions with effects
        clip_video = self.apply_captions(clip_video, caption_data)
        
        # Add cover image
        cover = self.generate_cover(clip_video, moment)
        
        # Final render
        output_path = self.render_final(clip_video, options)
        
        return {
            "id": clip_index + 1,
            "path": output_path,
            "cover": cover,
            "virality_score": moment["virality_score"],
            "title": moment["title"],
            "hook": moment["hook_text"]
        }
```

### 5.4 Performance Targets

| Metric | Target | Implementation |
|--------|--------|----------------|
| 1hr video → 10 clips | < 10 minutes | GPU workers (g4dn.xlarge) |
| Concurrent jobs | 50+ | Auto-scaling 0-10 instances |
| Time to first clip | < 3 minutes | Progressive rendering |
| Storage cost | < $0.01/video | S3 lifecycle policies |
| API latency (status) | < 50ms | Redis cache |

### 5.5 Cost Optimization

```python
COST_OPTIMIZATION_STRATEGIES = {
    "spot_instances": {
        "description": "Use EC2 Spot Instances for 70% cost reduction",
        "savings": "70%",
        "implementation": "Fallback to on-demand if spot unavailable"
    },
    "batch_processing": {
        "description": "Queue videos and process during off-peak hours",
        "savings": "40%",
        "implementation": "SQS delay queue + scheduling"
    },
    "model_caching": {
        "description": "Cache LLM responses for similar content",
        "savings": "30%",
        "implementation": "Redis cache with semantic similarity"
    },
    "progressive_rendering": {
        "description": "Start with low-quality preview, upgrade on demand",
        "savings": "50%",
        "implementation": "Two-pass encoding"
    }
}
```

---

## Implementation Priority Matrix

| Feature | Priority | Effort | Impact | Phase |
|---------|----------|--------|--------|-------|
| Fix mock transcript | P0 | Low | Critical | 1 |
| Enhanced LLM scoring | P0 | Medium | High | 1 |
| Face tracking (YOLO) | P1 | High | High | 2 |
| Smart captions | P1 | Medium | High | 2 |
| B-roll injection | P2 | High | Medium | 3 |
| Batch processing | P2 | High | High | 3 |
| Zoom effects | P3 | Medium | Medium | 4 |

---

## Model Recommendations Summary

| Task | Model | Cost | Latency | Notes |
|------|-------|------|---------|-------|
| Virality Analysis | Llama 4 Scout (Groq) | Low | 200ms | Current choice, excellent |
| Face Detection | YOLOv8n-face | Free | 5ms/frame | Self-hosted, no API cost |
| Object Tracking | ByteTrack | Free | 2ms/frame | Lightweight, real-time |
| Word Timestamps | Whisper Large v3 (Groq) | Low | 30s | Current choice |
| Semantic Analysis | Llama 4 Scout | Low | 150ms | For keyword highlighting |
| B-Roll Matching | CLIP ViT-B/32 | Free | 10ms | OpenAI's vision model |

---

## Next Steps

1. **Immediate (Week 1-2)**:
   - Fix mock transcript → use real STT output
   - Implement enhanced virality scoring
   - Add proper deduplication logic

2. **Short-term (Week 3-4)**:
   - Integrate YOLOv8 for face detection
   - Implement ByteTrack for smooth tracking
   - Build dynamic reframing pipeline

3. **Medium-term (Month 2)**:
   - Smart caption system with emoji injection
   - Keyword-based B-roll matching
   - Zoom effect system

4. **Long-term (Month 3+)**:
   - Cloud deployment (AWS/GCP)
   - Auto-scaling GPU workers
   - Batch processing pipeline
