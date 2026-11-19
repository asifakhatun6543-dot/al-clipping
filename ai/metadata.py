"""
AutoTube AI - AI Metadata Generator
Generates engaging titles, compliant descriptions, searchable tags, and categories.
Zero paid APIs - Runs 100% locally with intelligent NLP heuristic modeling.
"""

import re
from typing import Dict, Any, List
from collections import Counter
from services.logger import log_info

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "cannot", "could", "did", "do", "does", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here",
    "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "with", "would", "you", "your", "yours", "yourself", "yourselves", "um", "uh", "like"
}

CATEGORY_KEYWORDS = {
    "20": ["game", "gaming", "play", "player", "fps", "quest", "level", "boss", "gta", "minecraft"], # Gaming
    "28": ["ai", "tech", "code", "software", "computer", "future", "algorithm", "robot", "science"],  # Sci & Tech
    "27": ["learn", "tutorial", "how", "guide", "education", "study", "lesson", "knowledge"],        # Education
    "17": ["sport", "football", "fitness", "workout", "gym", "match", "goal", "athlete"],           # Sports
    "26": ["style", "fashion", "diy", "craft", "food", "cook", "recipe", "kitchen"],                 # Howto & Style
    "22": ["people", "story", "life", "vlog", "day", "experience", "talk", "family"]                # People & Blogs
}


class MetadataGenerator:
    def __init__(self, default_category_id: str = "24"):
        self.default_category_id = default_category_id

    def generate_metadata(
        self,
        clip_text: str,
        source_title: str = "Video",
        clip_number: int = 1
    ) -> Dict[str, Any]:
        """
        Generates YouTube Shorts metadata strictly adhering to community guidelines.
        """
        clean_text = clip_text.strip()
        
        # 1. Extract significant keywords
        words = re.findall(r"\b[a-zA-Z]{3,}\b", clean_text.lower())
        meaningful_words = [w for w in words if w not in STOP_WORDS]
        word_counts = Counter(meaningful_words)
        top_keywords = [w for w, _ in word_counts.most_common(8)]

        # 2. Generate Catchy Title (< 60 chars)
        title = self._craft_title(clean_text, top_keywords, source_title, clip_number)

        # 3. Generate Description
        description = self._craft_description(clean_text, title, top_keywords)

        # 4. Generate Hashtags
        hashtags = self._craft_hashtags(top_keywords)

        # 5. Detect YouTube Category
        category_id = self._detect_category(meaningful_words)

        log_info("MetadataGenerator", f"Generated metadata for clip #{clip_number}: '{title}'")
        return {
            "title": title,
            "description": description,
            "keywords": ", ".join(top_keywords[:10]),
            "hashtags": " ".join(hashtags),
            "category_id": category_id
        }

    def _craft_title(self, text: str, top_keywords: List[str], source_title: str, clip_number: int) -> str:
        """Crafts a concise hook title with #Shorts."""
        # Try finding a natural question or hook from the first sentence
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 5]
        first_sentence = sentences[0] if sentences else ""

        title_candidate = ""
        if first_sentence:
            # If first sentence is punchy (< 45 chars)
            if len(first_sentence) <= 45:
                title_candidate = first_sentence
            else:
                words = first_sentence.split()
                title_candidate = " ".join(words[:6])

        if not title_candidate:
            if top_keywords:
                topic = " ".join([w.capitalize() for w in top_keywords[:2]])
                title_candidate = f"The Truth About {topic}"
            else:
                title_candidate = f"{source_title} - Part {clip_number}"

        # Clean punctuation and append #Shorts
        title_candidate = title_candidate.rstrip(".,!?:- ")
        if len(title_candidate) > 48:
            title_candidate = title_candidate[:45] + "..."

        final_title = f"{title_candidate} ⚡ #Shorts"
        return final_title[:100]

    def _craft_description(self, text: str, title: str, top_keywords: List[str]) -> str:
        """Formats structured, SEO-friendly description."""
        summary = text[:300].strip()
        if len(text) > 300:
            summary += "..."

        topic_tag = top_keywords[0].capitalize() if top_keywords else "Insights"

        lines = [
            f"{title}",
            "",
            f"💡 In this Short: {summary}",
            "",
            "🔔 Subscribe for daily automated insights and high-value clips!",
            "",
            "#Shorts #Viral #Trending " + " ".join([f"#{w}" for w in top_keywords[:4]])
        ]
        return "\n".join(lines)

    def _craft_hashtags(self, top_keywords: List[str]) -> List[str]:
        tags = ["#Shorts", "#Viral", "#Trending"]
        for kw in top_keywords[:3]:
            tag = f"#{kw.capitalize()}"
            if tag not in tags:
                tags.append(tag)
        return tags

    def _detect_category(self, words: List[str]) -> str:
        """Determines best YouTube Category ID based on keyword matching."""
        scores = Counter()
        for cat_id, kws in CATEGORY_KEYWORDS.items():
            for kw in kws:
                if kw in words:
                    scores[cat_id] += 1

        if scores:
            return scores.most_common(1)[0][0]
        return self.default_category_id
