# Phase 3: Self-Improvement Features

> **Parent:** [M7 Analytics & Self-Improvement](../m7-analytics.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Analytics Pipeline) and Phase 2 (Dashboard) complete

---

## Goal

Implement intelligent self-improvement features that automatically identify content gaps, score response quality, and suggest improvements to enhance the AI agent's performance.

---

## Tasks

### 3.1 Content Gap Detection System

**Location:** `apps/api/app/analytics/gap_detection.py`

- [ ] Analyze low-confidence responses to identify knowledge gaps
- [ ] Use embedding similarity to cluster similar unanswered questions
- [ ] Surface topics that need better knowledge base coverage
- [ ] Prioritize gaps by frequency and business impact

**Gap Detection Algorithm:**

```python
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from sklearn.cluster import DBSCAN
from collections import Counter

@dataclass
class ContentGap:
    topic: str
    frequency: int
    confidence_threshold: float
    example_questions: List[str]
    suggested_priority: str  # 'high', 'medium', 'low'
    business_impact_score: float

@dataclass
class LowConfidenceResponse:
    conversation_id: UUID
    message: str
    response: str
    confidence_score: float
    timestamp: datetime
    embedding: List[float]

class ContentGapDetector:
    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
        self.confidence_threshold = 0.7  # Configurable
        self.min_cluster_size = 3

    async def detect_gaps(
        self,
        store_id: UUID,
        days_back: int = 30
    ) -> List[ContentGap]:
        """Detect content gaps for a store over the specified period."""

        # 1. Get low-confidence responses
        low_confidence_responses = await self._get_low_confidence_responses(
            store_id, days_back
        )

        if len(low_confidence_responses) < self.min_cluster_size:
            return []

        # 2. Cluster similar questions using embeddings
        clusters = await self._cluster_similar_questions(low_confidence_responses)

        # 3. Analyze each cluster to identify gaps
        gaps = []
        for cluster in clusters:
            gap = await self._analyze_cluster(cluster)
            if gap:
                gaps.append(gap)

        # 4. Prioritize gaps by business impact
        return sorted(gaps, key=lambda g: g.business_impact_score, reverse=True)

    async def _get_low_confidence_responses(
        self,
        store_id: UUID,
        days_back: int
    ) -> List[LowConfidenceResponse]:
        """Get responses with low confidence scores."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = """
        SELECT
            c.id as conversation_id,
            m.content as message,
            m.response as response,
            m.confidence_score,
            m.created_at,
            m.embedding
        FROM conversations c
        JOIN messages m ON c.id = m.conversation_id
        WHERE c.store_id = :store_id
        AND m.role = 'user'
        AND m.confidence_score < :threshold
        AND m.created_at >= :cutoff_date
        ORDER BY m.created_at DESC
        """

        result = await self.db.execute(
            text(query),
            {
                "store_id": store_id,
                "threshold": self.confidence_threshold,
                "cutoff_date": cutoff_date
            }
        )

        responses = []
        for row in result:
            responses.append(LowConfidenceResponse(
                conversation_id=row.conversation_id,
                message=row.message,
                response=row.response,
                confidence_score=row.confidence_score,
                timestamp=row.created_at,
                embedding=row.embedding
            ))

        return responses

    async def _cluster_similar_questions(
        self,
        responses: List[LowConfidenceResponse]
    ) -> List[List[LowConfidenceResponse]]:
        """Cluster similar questions using DBSCAN on embeddings."""
        if not responses:
            return []

        # Extract embeddings
        embeddings = np.array([r.embedding for r in responses])

        # Cluster using DBSCAN
        clustering = DBSCAN(eps=0.3, min_samples=self.min_cluster_size)
        cluster_labels = clustering.fit_predict(embeddings)

        # Group responses by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label == -1:  # Noise point
                continue
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(responses[i])

        return list(clusters.values())

    async def _analyze_cluster(
        self,
        cluster: List[LowConfidenceResponse]
    ) -> ContentGap | None:
        """Analyze a cluster to identify the content gap."""
        if len(cluster) < self.min_cluster_size:
            return None

        # Extract topic using LLM
        topic = await self._extract_topic_from_cluster(cluster)

        # Calculate business impact
        business_impact = self._calculate_business_impact(cluster)

        # Determine priority
        priority = self._determine_priority(len(cluster), business_impact)

        return ContentGap(
            topic=topic,
            frequency=len(cluster),
            confidence_threshold=np.mean([r.confidence_score for r in cluster]),
            example_questions=[r.message for r in cluster[:5]],
            suggested_priority=priority,
            business_impact_score=business_impact
        )

    async def _extract_topic_from_cluster(
        self,
        cluster: List[LowConfidenceResponse]
    ) -> str:
        """Use LLM to extract the main topic from a cluster of questions."""
        questions = [r.message for r in cluster[:10]]  # Limit for token efficiency

        prompt = f"""
        Analyze these customer questions and identify the main topic or theme:

        Questions:
        {chr(10).join(f"- {q}" for q in questions)}

        Provide a concise topic name (2-4 words) that captures what customers are asking about.
        Examples: "Shipping Times", "Return Policy", "Product Sizing", "Payment Methods"

        Topic:
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1
        )

        return response.choices[0].message.content.strip()

    def _calculate_business_impact(self, cluster: List[LowConfidenceResponse]) -> float:
        """Calculate business impact score based on frequency and recency."""
        frequency_score = min(len(cluster) / 10, 1.0)  # Normalize to 0-1

        # Recency score (more recent = higher impact)
        now = datetime.utcnow()
        avg_age_days = np.mean([
            (now - r.timestamp).days for r in cluster
        ])
        recency_score = max(0, 1 - (avg_age_days / 30))  # 30 days = 0 score

        return (frequency_score * 0.7) + (recency_score * 0.3)

    def _determine_priority(self, frequency: int, business_impact: float) -> str:
        """Determine priority level based on frequency and business impact."""
        if frequency >= 10 and business_impact >= 0.7:
            return "high"
        elif frequency >= 5 and business_impact >= 0.4:
            return "medium"
        else:
            return "low"
```

### 3.2 Quality Scoring System

**Location:** `apps/api/app/analytics/quality.py`

- [ ] Implement LLM-based response quality evaluation
- [ ] Score responses on helpfulness, accuracy, and politeness
- [ ] Track quality trends over time
- [ ] Identify responses that need improvement

**Quality Scoring Implementation:**

```python
from enum import Enum
from typing import Dict, List, Optional
import asyncio

class QualityDimension(str, Enum):
    HELPFULNESS = "helpfulness"
    ACCURACY = "accuracy"
    POLITENESS = "politeness"
    COMPLETENESS = "completeness"

@dataclass
class QualityScore:
    conversation_id: UUID
    overall_score: float
    dimension_scores: Dict[QualityDimension, float]
    feedback: str
    scored_at: datetime

class QualityScorer:
    def __init__(self, openai_client):
        self.openai_client = openai_client

    async def score_conversation(
        self,
        conversation_id: UUID,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> QualityScore:
        """Score the quality of a conversation."""

        # Format conversation for evaluation
        conversation_text = self._format_conversation(messages)

        # Get quality scores from LLM
        scores = await self._evaluate_with_llm(conversation_text, context)

        # Calculate overall score
        overall_score = np.mean(list(scores.values()))

        return QualityScore(
            conversation_id=conversation_id,
            overall_score=overall_score,
            dimension_scores=scores,
            feedback=await self._generate_feedback(scores, conversation_text),
            scored_at=datetime.utcnow()
        )

    async def _evaluate_with_llm(
        self,
        conversation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[QualityDimension, float]:
        """Use LLM to evaluate conversation quality."""

        prompt = f"""
        Evaluate this customer support conversation on the following dimensions.
        Rate each dimension from 0.0 to 1.0 (where 1.0 is excellent).

        Conversation:
        {conversation}

        Context: {context or "No additional context provided"}

        Please rate:
        1. Helpfulness: How well does the response address the customer's needs?
        2. Accuracy: Is the information provided correct and factual?
        3. Politeness: Is the tone professional and courteous?
        4. Completeness: Does the response fully answer the question?

        Respond in this exact JSON format:
        {{
            "helpfulness": 0.8,
            "accuracy": 0.9,
            "politeness": 1.0,
            "completeness": 0.7
        }}
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )

        try:
            scores_dict = json.loads(response.choices[0].message.content)
            return {
                QualityDimension.HELPFULNESS: scores_dict["helpfulness"],
                QualityDimension.ACCURACY: scores_dict["accuracy"],
                QualityDimension.POLITENESS: scores_dict["politeness"],
                QualityDimension.COMPLETENESS: scores_dict["completeness"],
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse quality scores: {e}")
            # Return default scores
            return {dim: 0.5 for dim in QualityDimension}

    async def _generate_feedback(
        self,
        scores: Dict[QualityDimension, float],
        conversation: str
    ) -> str:
        """Generate improvement feedback based on scores."""
        low_scores = [dim for dim, score in scores.items() if score < 0.6]

        if not low_scores:
            return "Good quality response overall."

        prompt = f"""
        Based on these quality scores, provide specific feedback for improvement:

        Scores: {scores}
        Low scoring areas: {low_scores}

        Conversation: {conversation}

        Provide 1-2 specific, actionable suggestions for improvement.
        Keep it concise and focused on the lowest scoring dimensions.
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation messages for evaluation."""
        formatted = []
        for msg in messages:
            role = "Customer" if msg["role"] == "user" else "Agent"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

# Background task to score conversations
@celery.task
async def score_recent_conversations():
    """Score conversations from the last 24 hours."""
    async with get_db_session() as db:
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Get unscored conversations
        query = """
        SELECT DISTINCT c.id, c.store_id
        FROM conversations c
        WHERE c.created_at >= :cutoff
        AND c.id NOT IN (
            SELECT conversation_id
            FROM conversation_quality_scores
            WHERE scored_at >= :cutoff
        )
        """

        result = await db.execute(text(query), {"cutoff": cutoff})

        scorer = QualityScorer(openai_client)

        for row in result:
            try:
                # Get conversation messages
                messages = await get_conversation_messages(db, row.id)

                # Score the conversation
                score = await scorer.score_conversation(row.id, messages)

                # Save to database
                await save_quality_score(db, score)

            except Exception as e:
                logger.error(f"Failed to score conversation {row.id}: {e}")
```

### 3.3 Auto Article Generation

**Location:** `apps/api/app/services/article_generation.py`

- [ ] Generate article drafts for identified content gaps
- [ ] Use store context and existing knowledge for consistency
- [ ] Create structured articles with proper formatting
- [ ] Queue articles for merchant review and approval

**Article Generation Service:**

```python
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class GeneratedArticle:
    title: str
    content: str
    topic: str
    suggested_tags: List[str]
    confidence_score: float
    source_questions: List[str]

class ArticleGenerator:
    def __init__(self, openai_client, knowledge_service: KnowledgeService):
        self.openai_client = openai_client
        self.knowledge_service = knowledge_service

    async def generate_article_for_gap(
        self,
        store_id: UUID,
        content_gap: ContentGap
    ) -> GeneratedArticle:
        """Generate an article to address a content gap."""

        # Get store context
        store_context = await self._get_store_context(store_id)

        # Get related existing knowledge
        related_knowledge = await self._get_related_knowledge(
            store_id, content_gap.topic
        )

        # Generate article content
        article_content = await self._generate_content(
            content_gap, store_context, related_knowledge
        )

        # Generate title and metadata
        title = await self._generate_title(content_gap.topic, article_content)
        tags = await self._generate_tags(content_gap.topic, article_content)

        return GeneratedArticle(
            title=title,
            content=article_content,
            topic=content_gap.topic,
            suggested_tags=tags,
            confidence_score=self._calculate_confidence(content_gap),
            source_questions=content_gap.example_questions
        )

    async def _generate_content(
        self,
        gap: ContentGap,
        store_context: Dict[str, Any],
        related_knowledge: List[str]
    ) -> str:
        """Generate article content using LLM."""

        prompt = f"""
        Write a comprehensive customer support article for an e-commerce store.

        Store Context:
        - Store Name: {store_context.get('name', 'Our Store')}
        - Industry: {store_context.get('industry', 'E-commerce')}
        - Existing Policies: {store_context.get('policies', 'Standard policies')}

        Topic: {gap.topic}

        Customer Questions (what prompted this article):
        {chr(10).join(f"- {q}" for q in gap.example_questions)}

        Related Existing Knowledge:
        {chr(10).join(related_knowledge) if related_knowledge else "No related knowledge found"}

        Requirements:
        1. Write in a helpful, professional tone
        2. Address the specific questions customers are asking
        3. Be consistent with existing store policies
        4. Include practical examples where relevant
        5. Structure with clear headings and bullet points
        6. Keep it concise but comprehensive

        Format the article in Markdown with:
        - Clear headings (##, ###)
        - Bullet points for lists
        - Bold text for emphasis
        - No title (will be generated separately)

        Article Content:
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    async def _generate_title(self, topic: str, content: str) -> str:
        """Generate a compelling title for the article."""
        prompt = f"""
        Create a clear, helpful title for this customer support article.

        Topic: {topic}

        Article content preview:
        {content[:500]}...

        Requirements:
        - Clear and descriptive
        - Customer-focused (what they want to know)
        - 5-10 words
        - No jargon

        Examples:
        - "How to Return Your Order"
        - "Shipping Times and Costs"
        - "Finding Your Perfect Size"

        Title:
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.2
        )

        return response.choices[0].message.content.strip().strip('"')

    async def _generate_tags(self, topic: str, content: str) -> List[str]:
        """Generate relevant tags for the article."""
        prompt = f"""
        Generate 3-5 relevant tags for this customer support article.

        Topic: {topic}
        Content: {content[:300]}...

        Tags should be:
        - Single words or short phrases
        - Relevant for search and categorization
        - Common terms customers would use

        Return as a comma-separated list.

        Tags:
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.2
        )

        tags_text = response.choices[0].message.content.strip()
        return [tag.strip() for tag in tags_text.split(',')]

    async def _get_store_context(self, store_id: UUID) -> Dict[str, Any]:
        """Get relevant store context for article generation."""
        # This would fetch store information, policies, etc.
        return {
            "name": "Example Store",
            "industry": "Fashion",
            "policies": "30-day returns, free shipping over $50"
        }

    async def _get_related_knowledge(
        self,
        store_id: UUID,
        topic: str
    ) -> List[str]:
        """Get existing knowledge related to the topic."""
        # Use vector search to find related content
        related_chunks = await self.knowledge_service.search_knowledge(
            store_id=store_id,
            query=topic,
            limit=3
        )

        return [chunk.content for chunk in related_chunks]

    def _calculate_confidence(self, gap: ContentGap) -> float:
        """Calculate confidence in the generated article."""
        # Higher frequency and lower existing confidence = higher confidence in generation
        frequency_factor = min(gap.frequency / 20, 1.0)
        gap_factor = 1.0 - gap.confidence_threshold

        return (frequency_factor * 0.6) + (gap_factor * 0.4)
```

### 3.4 LangSmith Integration

**Location:** `apps/api/app/integrations/langsmith.py`

- [ ] Integrate with LangSmith for advanced tracing
- [ ] Track all LLM calls with detailed metadata
- [ ] Create evaluation datasets from conversations
- [ ] Implement A/B testing for prompt variations

**LangSmith Integration:**

```python
from langsmith import Client as LangSmithClient
from langsmith.schemas import Run, Example
from typing import Dict, Any, List, Optional
import uuid

class LangSmithService:
    def __init__(self, api_key: str, project_name: str = "reva-ai"):
        self.client = LangSmithClient(api_key=api_key)
        self.project_name = project_name

    async def trace_chat_completion(
        self,
        conversation_id: UUID,
        store_id: UUID,
        messages: List[Dict[str, Any]],
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Trace a chat completion with LangSmith."""

        run_id = str(uuid.uuid4())

        # Create run
        run = Run(
            id=run_id,
            name="chat_completion",
            run_type="llm",
            inputs={
                "messages": messages,
                "conversation_id": str(conversation_id),
                "store_id": str(store_id)
            },
            outputs={"response": response},
            project_name=self.project_name,
            extra=metadata or {}
        )

        # Send to LangSmith
        self.client.create_run(run)

        return run_id

    async def trace_rag_retrieval(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        store_id: UUID,
        parent_run_id: Optional[str] = None
    ) -> str:
        """Trace RAG retrieval step."""

        run_id = str(uuid.uuid4())

        run = Run(
            id=run_id,
            name="rag_retrieval",
            run_type="retriever",
            inputs={"query": query, "store_id": str(store_id)},
            outputs={"chunks": retrieved_chunks},
            project_name=self.project_name,
            parent_run_id=parent_run_id
        )

        self.client.create_run(run)
        return run_id

    async def create_evaluation_dataset(
        self,
        store_id: UUID,
        name: str,
        conversations: List[Dict[str, Any]]
    ) -> str:
        """Create an evaluation dataset from conversations."""

        dataset = self.client.create_dataset(
            dataset_name=f"{name}_{store_id}",
            description=f"Evaluation dataset for store {store_id}"
        )

        examples = []
        for conv in conversations:
            example = Example(
                inputs={"messages": conv["messages"]},
                outputs={"expected_response": conv["expected_response"]},
                metadata={
                    "conversation_id": conv["conversation_id"],
                    "quality_score": conv.get("quality_score"),
                    "resolution_status": conv.get("resolution_status")
                }
            )
            examples.append(example)

        self.client.create_examples(
            inputs=[ex.inputs for ex in examples],
            outputs=[ex.outputs for ex in examples],
            metadata=[ex.metadata for ex in examples],
            dataset_id=dataset.id
        )

        return dataset.id

    async def run_evaluation(
        self,
        dataset_id: str,
        evaluator_name: str = "response_quality"
    ) -> Dict[str, Any]:
        """Run evaluation on a dataset."""

        # This would integrate with LangSmith's evaluation framework
        # For now, return placeholder results
        return {
            "dataset_id": dataset_id,
            "evaluator": evaluator_name,
            "results": {
                "accuracy": 0.85,
                "helpfulness": 0.78,
                "avg_score": 0.815
            }
        }

# Integration with existing chat service
class EnhancedChatService(ChatService):
    def __init__(self, db: AsyncSession, langsmith: LangSmithService):
        super().__init__(db)
        self.langsmith = langsmith

    async def generate_response(
        self,
        conversation_id: UUID,
        message: str,
        store_id: UUID
    ) -> Dict[str, Any]:
        """Enhanced response generation with LangSmith tracing."""

        # Start parent trace
        parent_run_id = str(uuid.uuid4())

        # Trace retrieval
        retrieved_chunks = await self.retrieve_context(message, store_id)
        retrieval_run_id = await self.langsmith.trace_rag_retrieval(
            query=message,
            retrieved_chunks=[chunk.to_dict() for chunk in retrieved_chunks],
            store_id=store_id,
            parent_run_id=parent_run_id
        )

        # Generate response
        response = await super().generate_response(conversation_id, message, store_id)

        # Trace completion
        await self.langsmith.trace_chat_completion(
            conversation_id=conversation_id,
            store_id=store_id,
            messages=[{"role": "user", "content": message}],
            response=response["response"],
            metadata={
                "retrieval_run_id": retrieval_run_id,
                "chunks_count": len(retrieved_chunks),
                "confidence_score": response.get("confidence_score")
            }
        )

        return response
```

### 3.5 Self-Improvement Dashboard

**Location:** `apps/web/app/(dashboard)/analytics/improvements/page.tsx`

- [ ] Display identified content gaps
- [ ] Show generated article drafts for review
- [ ] Quality score trends and insights
- [ ] LangSmith evaluation results

```tsx
'use client';

import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface ContentGap {
  id: string;
  topic: string;
  frequency: number;
  priority: 'high' | 'medium' | 'low';
  exampleQuestions: string[];
  status: 'identified' | 'in_progress' | 'resolved';
}

interface GeneratedArticle {
  id: string;
  title: string;
  content: string;
  topic: string;
  confidenceScore: number;
  status: 'draft' | 'review' | 'approved' | 'published';
}

export default function ImprovementsPage() {
  const [contentGaps, setContentGaps] = useState<ContentGap[]>([]);
  const [generatedArticles, setGeneratedArticles] = useState<GeneratedArticle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchImprovementData();
  }, []);

  const fetchImprovementData = async () => {
    setLoading(true);
    try {
      const [gapsResponse, articlesResponse] = await Promise.all([
        fetch('/api/analytics/content-gaps'),
        fetch('/api/analytics/generated-articles'),
      ]);

      const gaps = await gapsResponse.json();
      const articles = await articlesResponse.json();

      setContentGaps(gaps);
      setGeneratedArticles(articles);
    } catch (error) {
      console.error('Failed to fetch improvement data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateArticle = async (gapId: string) => {
    try {
      await fetch(`/api/analytics/content-gaps/${gapId}/generate-article`, {
        method: 'POST',
      });

      // Refresh data
      fetchImprovementData();
    } catch (error) {
      console.error('Failed to generate article:', error);
    }
  };

  const approveArticle = async (articleId: string) => {
    try {
      await fetch(`/api/analytics/generated-articles/${articleId}/approve`, {
        method: 'POST',
      });

      fetchImprovementData();
    } catch (error) {
      console.error('Failed to approve article:', error);
    }
  };

  if (loading) {
    return <div>Loading improvements...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Self-Improvement</h1>
        <Button onClick={fetchImprovementData}>Refresh Analysis</Button>
      </div>

      <Tabs defaultValue="gaps" className="space-y-4">
        <TabsList>
          <TabsTrigger value="gaps">Content Gaps</TabsTrigger>
          <TabsTrigger value="articles">Generated Articles</TabsTrigger>
          <TabsTrigger value="quality">Quality Insights</TabsTrigger>
        </TabsList>

        <TabsContent value="gaps" className="space-y-4">
          <div className="grid gap-4">
            {contentGaps.map((gap) => (
              <Card key={gap.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{gap.topic}</CardTitle>
                      <p className="text-sm text-gray-600">{gap.frequency} customer questions</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge
                        variant={
                          gap.priority === 'high'
                            ? 'destructive'
                            : gap.priority === 'medium'
                              ? 'default'
                              : 'secondary'
                        }
                      >
                        {gap.priority} priority
                      </Badge>
                      <Badge variant="outline">{gap.status}</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <h4 className="mb-2 font-medium">Example Questions:</h4>
                      <ul className="space-y-1 text-sm text-gray-600">
                        {gap.exampleQuestions.slice(0, 3).map((question, i) => (
                          <li key={i}>• {question}</li>
                        ))}
                      </ul>
                    </div>

                    {gap.status === 'identified' && (
                      <Button onClick={() => generateArticle(gap.id)} size="sm">
                        Generate Article
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="articles" className="space-y-4">
          <div className="grid gap-4">
            {generatedArticles.map((article) => (
              <Card key={article.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{article.title}</CardTitle>
                      <p className="text-sm text-gray-600">
                        Topic: {article.topic} • Confidence:{' '}
                        {(article.confidenceScore * 100).toFixed(0)}%
                      </p>
                    </div>
                    <Badge variant="outline">{article.status}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="prose prose-sm max-w-none">
                      <div className="line-clamp-3 text-sm text-gray-600">
                        {article.content.substring(0, 200)}...
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button size="sm" variant="outline">
                        Preview
                      </Button>
                      {article.status === 'draft' && (
                        <Button size="sm" onClick={() => approveArticle(article.id)}>
                          Approve & Publish
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="quality">
          <Card>
            <CardHeader>
              <CardTitle>Quality Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Quality scoring and improvement suggestions will be displayed here.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

## Files to Create/Modify

| File                                                       | Action | Purpose                             |
| ---------------------------------------------------------- | ------ | ----------------------------------- |
| `app/analytics/gap_detection.py`                           | Create | Content gap detection algorithms    |
| `app/analytics/quality.py`                                 | Create | Response quality scoring system     |
| `app/services/article_generation.py`                       | Create | Auto article generation service     |
| `app/integrations/langsmith.py`                            | Create | LangSmith API integration           |
| `app/api/v1/improvements.py`                               | Create | Self-improvement API endpoints      |
| `app/workers/improvement_tasks.py`                         | Create | Background improvement tasks        |
| `apps/web/app/(dashboard)/analytics/improvements/page.tsx` | Create | Self-improvement dashboard page     |
| `apps/web/components/improvements/gap-card.tsx`            | Create | Content gap display component       |
| `apps/web/components/improvements/article-preview.tsx`     | Create | Generated article preview component |

---

## Dependencies

```toml
# Add to apps/api/pyproject.toml
langsmith = "^0.1"           # LangSmith integration
scikit-learn = "^1.3"        # Clustering algorithms
```

---

## Testing

- [ ] Unit test: content gap detection accuracy
- [ ] Unit test: quality scoring consistency
- [ ] Unit test: article generation quality
- [ ] Integration test: LangSmith tracing works correctly
- [ ] E2E test: full self-improvement workflow
- [ ] Performance test: gap detection on large datasets

---

## Acceptance Criteria

1. Content gaps are identified accurately from low-confidence responses
2. Quality scores correlate with human evaluation (>0.8 correlation)
3. Generated articles address the identified gaps effectively
4. LangSmith integration provides detailed tracing for all LLM calls
5. Self-improvement dashboard provides actionable insights
6. Background tasks run efficiently without impacting performance

---

## Notes

- Start with simple gap detection, improve algorithms iteratively
- Quality scoring should be calibrated with human feedback
- Generated articles need human review before publishing
- LangSmith integration should be optional (graceful degradation)
- Consider implementing feedback loops to improve detection accuracy
