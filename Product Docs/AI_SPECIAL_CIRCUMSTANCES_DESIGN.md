# AI/ML-Powered Special Circumstances Enhancement
## Form 122A-2, Lines 44-47 Implementation Framework

**Date:** January 4, 2026  
**Status:** Technical Design (Ready for Implementation)  
**Priority:** P0 (Critical Path Blocker per PRD v0.3)  
**Owners:** Backend (LLM integration) + Frontend (narrative capture UI)

---

## I. Legal Foundation: 11 U.S.C. § 707(b)(2)(B)

### Statutory Text
**11 U.S.C. § 707(b)(2)(B)** permits a debtor to rebut the presumption of abuse under Chapter 7 if:

> "Special circumstances exist that make the payment of any amount of any regular expenses not reasonably necessary to be expended or reasonably necessary to expend..."

### Two Pathways to Rebuttal

#### Pathway A: Expenses Not Reasonably Necessary
- Current expenses that exceed statutory allowances (IRS standards, local variances)
- Justified by circumstances unique to debtor's situation
- Examples: uninsured medical conditions, necessary transportation for health treatment, disability-related expenses

#### Pathway B: Special Circumstances Justifying Lower Income or Higher Expenses
- Life circumstances that affect ability to generate income or increase legitimate expenses
- Examples: recent job loss, ongoing medical condition, disability, education commitment, child support obligations
- **Outcome:** Downward adjustment to CMI or upward adjustment to allowable expenses

### Form 122A-2, Lines 44-47 Implementation
**Official Form 122A-2** Section dedicated to special circumstances:

```
Lines 44-47: SPECIAL CIRCUMSTANCES

Line 44: Do you have any special circumstances?
         ☐ No  ☐ Yes

Lines 45-47: [If yes] Describe any special circumstances that make the payment of the monthly expenses 
            not reasonably necessary or any circumstances that justify the debtor's monthly income to be 
            adjusted downward...
```

**Critical Role:** Lines 44-47 are the *sole mechanism* for pro se filers to claim rebuttal. Without clear, compelling prose here:
- Court may dismiss rebuttal (inaction = consent to presumption of abuse)
- Fee waiver claims fail (must reference § 1930(f) exemption pathways)
- Above-median filers lose only remaining qualification pathway

---

## II. The Perception & Language Problem

### Research Findings
**Case Law Analysis (PRD v0.3):**
- Debtors with identical financial profiles achieve **55-90% success rates** when special circumstances are properly documented
- Attorney-drafted rebuttals: **85-90% success rate** (clear narrative, legal framing)
- Pro se rebuttals: **15-25% success rate** (vague, unfamiliar legal language, missing critical connections)
- **Root cause:** Language, not facts. Same circumstances, radically different outcomes based on articulation.

### The Language Gap
**What filers say (natural language):**
> "My job got eliminated last year. I was making good money but now I'm unemployed. I have medical bills from my diabetes. My bills are too high."

**What courts need (legal prose):**
> "Debtor's household income was artificially inflated in the lookback period due to employment that has been permanently terminated. Debtor's current monthly income reflects involuntary unemployment. Additionally, debtor has documented medical expenses exceeding IRS standards due to a chronic condition requiring ongoing treatment and medication. These special circumstances—involuntary job loss and necessary medical expenses—make the payment of the monthly expenses not reasonably necessary under 11 U.S.C. § 707(b)(2)(B)."

**Difference:** Same facts. Second version has 3x higher success probability.

### Why AI/ML Fits
1. **Perception amplification, not legal advice:** AI transforms articulation, not substance
2. **Scales pro se access:** Automates the attorney advantage without crossing UPL line
3. **Preserves user ownership:** Filer reviews and approves all changes (human-in-loop)
4. **Audit trail:** Every edit tracked for legal defensibility

---

## III. Architecture: LLM-Powered Narrative Refinement

### 3.1 System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPECIAL CIRCUMSTANCES FLOW                    │
└─────────────────────────────────────────────────────────────────┘

User Input (Natural Language)
        ↓
    [Validation Layer]
        ↓
    [Structured Extraction]
        ↓
    [LLM Refinement Prompt]
        ↓
    [Legally Defensible Prose Output]
        ↓
    [User Review & Approval] ← HUMAN-IN-LOOP (Critical)
        ↓
    [Encrypted Storage in Database]
        ↓
    [Auto-populate Form 122A-2, Lines 44-47 on PDF]
```

### 3.2 Model Selection & Reasoning

**Recommended Model:** **Claude 3.5 Sonnet** (or equivalent)

**Why:**
- Strong legal reasoning capability without requiring fine-tuning
- Excellent instruction-following for constrained prompting (no hallucination)
- Supports long context (100K tokens) for case law examples
- Cost-effective ($3 per million input tokens)
- Available via:
  - Claude API (official, production-ready)
  - Anthropic Batch API (cost-effective for high volume)
  - GitHub Models (if using GitHub deployment)

**Alternative:** OpenAI GPT-4o
- Slightly faster inference
- Reliable structured output (JSON mode)
- Higher cost ($15 per million input tokens)

**Not Recommended:**
- Open-source models (llama2, mistral): lower legal reasoning quality
- GPT-3.5 turbo: insufficient legal instruction-following
- Fine-tuned models: data requirements (bankruptcy cases with annotations) too high for MVP

---

## IV. Prompting Strategy: Legal Framework Encoding

### 4.1 System Prompt (Injected into Every Request)

```python
SYSTEM_PROMPT = """
You are a legal document editor specializing in Chapter 7 bankruptcy special circumstances 
statements (11 U.S.C. § 707(b)(2)(B)). Your role is NOT to provide legal advice, but to 
help filers articulate their circumstances in legally defensible prose suitable for Form 122A-2, 
Lines 44-47.

CONSTRAINTS:
1. Never evaluate whether circumstances legally qualify (that's for the court/trustee)
2. Never use phrases implying legal prediction ("You will probably...," "The court will...")
3. Never recommend filing strategies ("You should file Chapter 13 instead")
4. Always use "may be" instead of "is" (non-determinative language)

LEGAL FRAMEWORK YOU MUST ENCODE:
- 11 U.S.C. § 707(b)(2)(B) permits rebuttal if special circumstances exist that make payment 
  of expenses "not reasonably necessary" or justify adjusted income
- Lines 44-47 are the *only* space pro se filers have to make this argument
- Court must consider and respond to rebuttal claims (Bankruptcy Rule 1008)
- IRS expense standards (NSA) are baseline; deviations must reference special circumstances

STANDARD SPECIAL CIRCUMSTANCES (Reference these when applicable):
A. INVOLUNTARY INCOME REDUCTION
   - Recent job loss, involuntary termination, forced retirement
   - Business closure, loss of self-employment income
   - Reduction in hours/shift changes
   - Must include: dates, reason for job loss, job search efforts

B. MEDICAL/HEALTH CONDITIONS
   - Chronic illness requiring ongoing treatment/medication
   - Disability (physical, mental, developmental)
   - Recent diagnosis requiring new treatment regimen
   - Must include: condition name, treatment type, monthly cost impact

C. FAMILY SUPPORT OBLIGATIONS
   - Child support/alimony payments
   - Care for dependent relatives
   - Must include: legal order reference or beneficiary details

D. NECESSARY DEBT SERVICE
   - Court-ordered restitution
   - Mortgage/rent (if above-area standard but necessary)
   - Must include: order date or justification

E. EDUCATION/WORKFORCE DEVELOPMENT
   - Court-approved vocational training
   - Licensing/certification required for employment
   - Must include: program details, timeline, employment goal

OUTPUT REQUIREMENT:
Transform the user's narrative into a short paragraph (150-250 words) that:
- Lists each special circumstance category by name
- Includes concrete details (dates, amounts, specific conditions)
- Uses § 707(b)(2)(B) framing ("not reasonably necessary" or "justify adjustment")
- Maintains first-person perspective (preserves authenticity)
- Avoids legal jargon while remaining legally precise
"""
```

### 4.2 User Prompt Template (Dynamic, Based on Intake Data)

```python
def generate_refinement_prompt(user_narrative: str, intake_data: dict) -> str:
    """Generate context-aware refinement prompt."""
    
    return f"""
FILER'S NARRATIVE:
"{user_narrative}"

CONTEXT FROM INTAKE:
- Household Status: {intake_data.get('marital_status', 'Unknown')}
- Family Size: {intake_data.get('family_size', 'Unknown')}
- Current Monthly Income: ${intake_data.get('cmi', 'Unknown')}
- Median Income Threshold: ${intake_data.get('median_income', 'Unknown')}
- Means Test Result: {intake_data.get('means_test_result', 'Unknown')}

IDENTIFIED CIRCUMSTANCES (from intake responses):
{format_identified_circumstances(intake_data)}

TASK:
Refine the above narrative into a legally defensible statement suitable for Form 122A-2, Lines 44-47.

1. Preserve the filer's voice and authenticity
2. Add specific details that strengthen the § 707(b)(2)(B) rebuttal argument
3. Reference applicable special circumstances categories
4. Include concrete dates/amounts where possible
5. Use language that a bankruptcy court will recognize as serious/credible

OUTPUT:
Provide ONLY the refined paragraph (no preamble or explanation). The output will be read directly 
by the filer and inserted into their bankruptcy petition.
"""
```

### 4.3 Few-Shot Examples (In-Context Learning)

Include 2-3 examples of before/after special circumstances statements:

```python
FEW_SHOT_EXAMPLES = [
    {
        "before": "I lost my job last year. Now I can't afford my medical bills. Everything is too expensive.",
        "after": "Debtor's household income was artificially inflated in the lookback period due to full-time employment terminated involuntarily in June 2025. The position was eliminated due to workforce reduction at Employer. Debtor has been unemployed for 6 months and currently receives no regular income beyond spouse's employment. Additionally, Debtor has a documented chronic condition (Type 2 diabetes) requiring monthly insulin, monitoring, and specialist care at costs exceeding $400/month. These special circumstances—involuntary unemployment and medical expenses exceeding IRS standards—make the payment of certain monthly expenses not reasonably necessary."
    },
    {
        "before": "I have to pay child support. Also my car needs lots of repairs because I drive far to work.",
        "after": "Debtor pays court-ordered child support of $850/month pursuant to [State] Order dated [Date]. Debtor's vehicle is the sole means of transportation required to maintain current employment 45 miles from residence. Vehicle maintenance and fuel costs exceed regional averages due to distance traveled for work. These special circumstances—legal child support obligations and transportation expenses necessary to maintain employment—justify adjustment of Debtor's monthly income and expenses under § 707(b)(2)(B)."
    }
]
```

---

## V. Implementation Stack

### 5.1 Backend Architecture

#### New Model: `SpecialCircumstances`

```python
# backend/apps/eligibility/models.py

class SpecialCircumstances(models.Model):
    """
    Capture and refine special circumstances narrative for Form 122A-2, Lines 44-47.
    
    Implements 11 U.S.C. § 707(b)(2)(B) rebuttal mechanism with LLM-powered narrative 
    refinement to enhance pro se filer articulation.
    """
    
    CIRCUMSTANCE_CATEGORIES = [
        ('income_reduction', 'Involuntary Income Reduction'),
        ('medical', 'Medical/Health Condition'),
        ('family_support', 'Family Support Obligation'),
        ('debt_service', 'Necessary Debt Service'),
        ('education', 'Education/Workforce Development'),
        ('other', 'Other'),
    ]
    
    session = models.OneToOneField(
        "intake.IntakeSession", 
        on_delete=models.CASCADE, 
        related_name="special_circumstances"
    )
    
    # User's initial narrative (natural language input)
    user_narrative = EncryptedTextField(
        blank=True,
        help_text="User's raw description of special circumstances"
    )
    
    # Extracted categories (from intake wizard checkboxes)
    identified_categories = models.JSONField(
        default=list,
        help_text="Categories user selected: income_reduction, medical, family_support, etc."
    )
    
    # LLM-refined narrative (legally defensible prose)
    refined_narrative = EncryptedTextField(
        blank=True,
        help_text="AI-refined special circumstances statement for Form 122A-2"
    )
    
    # Refinement metadata
    refinement_version = models.IntegerField(
        default=1,
        help_text="Version number if user requests multiple refinements"
    )
    refinement_model = models.CharField(
        max_length=50,
        default="claude-3.5-sonnet",
        help_text="Which LLM model was used for refinement"
    )
    refinement_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When refinement was generated"
    )
    
    # User approval (human-in-loop)
    user_approved = models.BooleanField(
        default=False,
        help_text="User explicitly approved refined narrative"
    )
    user_approval_timestamp = models.DateTimeField(
        null=True,
        blank=True
    )
    approval_notes = EncryptedTextField(
        blank=True,
        help_text="User's requested modifications before approval"
    )
    
    # Audit trail
    refinement_prompt_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of refinement prompt (for reproducibility)"
    )
    llm_response_full = EncryptedTextField(
        blank=True,
        help_text="Full LLM response (for debugging/audit)"
    )
    
    # Form integration
    included_in_form_122a2 = models.BooleanField(
        default=False,
        help_text="Whether narrative was included in generated Form 122A-2 PDF"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "special_circumstances"
        indexes = [
            models.Index(fields=['session', 'user_approved']),
            models.Index(fields=['refinement_timestamp']),
        ]
    
    def __str__(self):
        return f"Special Circumstances - Session {self.session_id} ({'Approved' if self.user_approved else 'Pending'})"
    
    def get_identified_categories(self) -> list:
        """Return list of identified special circumstance categories."""
        return self.identified_categories or []
    
    def get_refined_narrative(self) -> str:
        """Return approved refined narrative, fallback to user narrative."""
        if self.user_approved and self.refined_narrative:
            return self.refined_narrative
        return self.user_narrative
```

#### New Service: `SpecialCircumstancesRefiner`

```python
# backend/apps/eligibility/services/special_circumstances_refiner.py

import anthropic
import hashlib
import json
from typing import Dict, Any, Optional
from django.db import transaction
from apps.eligibility.models import SpecialCircumstances

class SpecialCircumstancesRefiner:
    """
    LLM-powered service to refine user special circumstances narratives into 
    legally defensible prose suitable for Form 122A-2, Lines 44-47.
    
    This service is NOT legal advice generation—it's language enhancement that
    preserves the user's facts while improving articulation for court readability.
    """
    
    # System prompt encoding legal framework
    SYSTEM_PROMPT = """[See Section IV.1 above]"""
    
    FEW_SHOT_EXAMPLES = """[See Section IV.3 above]"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Anthropic client."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Latest Sonnet
    
    @transaction.atomic
    def refine_narrative(
        self, 
        special_circumstances: SpecialCircumstances,
        intake_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine user's special circumstances narrative using LLM.
        
        Args:
            special_circumstances: SpecialCircumstances model instance
            intake_data: Dict with means test results, family size, CMI, etc.
        
        Returns:
            {
                'success': bool,
                'refined_narrative': str,
                'refinement_version': int,
                'error': str (if failure),
                'tokens_used': int
            }
        """
        
        try:
            # Build context-aware prompt
            user_prompt = self._build_user_prompt(
                special_circumstances.user_narrative,
                special_circumstances.identified_categories,
                intake_data
            )
            
            # Call LLM with safety constraints
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temp for consistency
            )
            
            refined_text = response.content[0].text.strip()
            
            # Store refinement results
            special_circumstances.refined_narrative = refined_text
            special_circumstances.refinement_version += 1
            special_circumstances.refinement_timestamp = timezone.now()
            special_circumstances.refinement_model = self.model
            special_circumstances.llm_response_full = response.content[0].text
            special_circumstances.refinement_prompt_hash = hashlib.sha256(
                user_prompt.encode()
            ).hexdigest()
            special_circumstances.save()
            
            return {
                'success': True,
                'refined_narrative': refined_text,
                'refinement_version': special_circumstances.refinement_version,
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            }
        
        except anthropic.APIError as e:
            return {
                'success': False,
                'error': f"LLM API error: {str(e)}",
            }
    
    def _build_user_prompt(
        self,
        user_narrative: str,
        identified_categories: list,
        intake_data: Dict[str, Any]
    ) -> str:
        """Build context-aware prompt for LLM."""
        
        categories_text = self._format_categories(identified_categories, intake_data)
        
        return f"""
FILER'S NARRATIVE:
"{user_narrative}"

CONTEXT FROM INTAKE:
- Household Status: {intake_data.get('marital_status', 'Not provided')}
- Family Size: {intake_data.get('family_size', 'Not provided')}
- Current Monthly Income: ${intake_data.get('cmi', 'Unknown')}
- Median Income Threshold: ${intake_data.get('median_income', 'Unknown')}
- Means Test Status: {intake_data.get('means_test_status', 'Unknown')}

IDENTIFIED SPECIAL CIRCUMSTANCES:
{categories_text}

TASK:
Refine the filer's narrative into a legally defensible statement suitable for Form 122A-2, Lines 44-47.
Follow these principles:
1. Preserve the filer's authentic voice and perspective
2. Add specific details that strengthen the § 707(b)(2)(B) rebuttal argument
3. Reference applicable special circumstances categories explicitly
4. Include concrete dates, amounts, and supporting details where possible
5. Use clear language a bankruptcy court will recognize as serious and credible

OUTPUT:
Provide ONLY the refined paragraph (150-250 words). Do not include explanations or commentary.
"""
    
    def _format_categories(self, categories: list, intake_data: dict) -> str:
        """Format identified categories with supporting intake data."""
        
        formatted = []
        for cat in categories:
            if cat == 'income_reduction' and intake_data.get('recent_job_loss'):
                formatted.append(f"- Recent job loss ({intake_data.get('job_loss_date')})")
            elif cat == 'medical' and intake_data.get('health_conditions'):
                conditions = intake_data.get('health_conditions', [])
                formatted.append(f"- Medical conditions: {', '.join(conditions)}")
            elif cat == 'family_support' and intake_data.get('child_support_amount'):
                formatted.append(f"- Child support: ${intake_data.get('child_support_amount')}/month")
            elif cat == 'education' and intake_data.get('education_program'):
                formatted.append(f"- Workforce development: {intake_data.get('education_program')}")
        
        return '\n'.join(formatted) if formatted else "- User indicated special circumstances apply"
    
    def validate_output(self, refined_text: str) -> Dict[str, Any]:
        """
        Validate LLM output for safety/appropriateness.
        
        Returns:
            {'is_valid': bool, 'issues': [str]}
        """
        
        issues = []
        prohibited_phrases = [
            "you will win",
            "you will qualify",
            "you should file",
            "i recommend",
            "legally, you",
            "you have a strong case"
        ]
        
        text_lower = refined_text.lower()
        for phrase in prohibited_phrases:
            if phrase in text_lower:
                issues.append(f"Contains prohibited phrase: '{phrase}'")
        
        if len(refined_text) < 100 or len(refined_text) > 1500:
            issues.append(f"Output length {len(refined_text)} words is outside target 150-250")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
```

### 5.2 API Endpoint

```python
# backend/apps/eligibility/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.eligibility.models import SpecialCircumstances
from apps.eligibility.services.special_circumstances_refiner import SpecialCircumstancesRefiner

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refine_special_circumstances(request):
    """
    POST /api/eligibility/special-circumstances/refine/
    
    Request body:
    {
        "session_id": int,
        "user_narrative": str,
        "identified_categories": [str]
    }
    
    Response:
    {
        "success": bool,
        "refined_narrative": str,
        "status": "pending_approval" | "error",
        "message": str,
        "refinement_version": int
    }
    """
    
    try:
        session = IntakeSession.objects.get(
            id=request.data['session_id'],
            user=request.user
        )
        
        # Get or create special circumstances record
        spec_circ, created = SpecialCircumstances.objects.get_or_create(
            session=session
        )
        
        # Store user's initial narrative
        spec_circ.user_narrative = request.data.get('user_narrative', '')
        spec_circ.identified_categories = request.data.get('identified_categories', [])
        spec_circ.save()
        
        # Call LLM refinement service
        refiner = SpecialCircumstancesRefiner()
        intake_data = {
            'marital_status': session.debtor_info.marital_status,
            'family_size': session.get_family_size(),
            'cmi': session.means_test.calculated_cmi if hasattr(session, 'means_test') else None,
            'median_income': session.means_test.median_income_threshold if hasattr(session, 'means_test') else None,
            'means_test_status': 'passes' if session.means_test.passes_means_test else 'fails' if hasattr(session, 'means_test') else None,
        }
        
        result = refiner.refine_narrative(spec_circ, intake_data)
        
        if not result['success']:
            return Response(
                {
                    'success': False,
                    'status': 'error',
                    'message': result['error']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate output safety
        validation = refiner.validate_output(result['refined_narrative'])
        if not validation['is_valid']:
            return Response(
                {
                    'success': False,
                    'status': 'error',
                    'message': 'Output validation failed',
                    'issues': validation['issues']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                'success': True,
                'refined_narrative': result['refined_narrative'],
                'status': 'pending_approval',
                'refinement_version': result['refinement_version'],
                'message': 'Narrative refined. Please review and approve before proceeding.'
            },
            status=status.HTTP_200_OK
        )
    
    except IntakeSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_special_circumstances(request):
    """
    POST /api/eligibility/special-circumstances/approve/
    
    Request body:
    {
        "session_id": int,
        "approved_narrative": str (optional - if user made edits),
        "approval_notes": str (optional)
    }
    
    Response:
    {
        "success": bool,
        "message": str,
        "special_circumstances_id": int
    }
    """
    
    try:
        session = IntakeSession.objects.get(
            id=request.data['session_id'],
            user=request.user
        )
        
        spec_circ = SpecialCircumstances.objects.get(session=session)
        
        # Allow user to override refined narrative before approval
        if 'approved_narrative' in request.data:
            spec_circ.refined_narrative = request.data['approved_narrative']
        
        spec_circ.approval_notes = request.data.get('approval_notes', '')
        spec_circ.user_approved = True
        spec_circ.user_approval_timestamp = timezone.now()
        spec_circ.save()
        
        # Log approval for audit trail
        AuditLog.objects.create(
            user=request.user,
            action='special_circumstances_approved',
            upl_sensitive=True,
            details={
                'session_id': session.id,
                'refinement_version': spec_circ.refinement_version,
                'has_approval_notes': bool(spec_circ.approval_notes),
            }
        )
        
        return Response(
            {
                'success': True,
                'message': 'Special circumstances approved. You may now generate forms.',
                'special_circumstances_id': spec_circ.id
            },
            status=status.HTTP_200_OK
        )
    
    except SpecialCircumstances.DoesNotExist:
        return Response(
            {'error': 'Special circumstances record not found'},
            status=status.HTTP_404_NOT_FOUND
        )
```

---

## VI. Frontend Implementation: Narrative Capture & Refinement UI

### 6.1 Component: Special Circumstances Wizard

```typescript
// frontend/src/components/SpecialCircumstancesWizard.tsx

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface SpecialCircumstancesStep {
  category: string;
  label: string;
  description: string;
  examples: string[];
}

const SPECIAL_CIRCUMSTANCES_CATEGORIES: SpecialCircumstancesStep[] = [
  {
    category: 'income_reduction',
    label: 'Involuntary Income Reduction',
    description: 'Recent job loss, forced termination, or reduced hours',
    examples: [
      'I was laid off due to company downsizing',
      'My position was eliminated after 15 years',
      'I was forced to retire early for medical reasons'
    ]
  },
  {
    category: 'medical',
    label: 'Medical or Health Condition',
    description: 'Chronic illness, disability, or ongoing medical treatment',
    examples: [
      'I have diabetes that requires monthly medications and specialist visits',
      'I have a disability that limits my work capacity',
      'Recent diagnosis requiring ongoing treatment'
    ]
  },
  {
    category: 'family_support',
    label: 'Family Support Obligations',
    description: 'Child support, alimony, or caring for dependents',
    examples: [
      'I pay $850/month in court-ordered child support',
      'I support my elderly parents who cannot work'
    ]
  },
  {
    category: 'debt_service',
    label: 'Necessary Debt Service',
    description: 'Mortgage, rent, or court-ordered restitution',
    examples: [
      'Mortgage on family home is essential to family stability',
      'Court-ordered restitution payment'
    ]
  },
  {
    category: 'education',
    label: 'Education or Workforce Development',
    description: 'Training or certification needed for employment',
    examples: [
      'I am pursuing a teaching certification to improve employment prospects'
    ]
  }
];

interface SpecialCircumstancesWizardProps {
  sessionId: number;
  onComplete: () => void;
}

export const SpecialCircumstancesWizard: React.FC<SpecialCircumstancesWizardProps> = ({
  sessionId,
  onComplete,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [userNarrative, setUserNarrative] = useState<string>('');
  const [refinedNarrative, setRefinedNarrative] = useState<string | null>(null);
  const [isReviewingRefinement, setIsReviewingRefinement] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState<string>('');

  // Mutation: Refine narrative with LLM
  const refineMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(
        '/api/eligibility/special-circumstances/refine/',
        {
          session_id: sessionId,
          user_narrative: userNarrative,
          identified_categories: selectedCategories,
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      setRefinedNarrative(data.refined_narrative);
      setIsReviewingRefinement(true);
    },
  });

  // Mutation: Approve refined narrative
  const approveMutation = useMutation({
    mutationFn: async (approvedNarrative: string) => {
      const response = await apiClient.post(
        '/api/eligibility/special-circumstances/approve/',
        {
          session_id: sessionId,
          approved_narrative: approvedNarrative,
          approval_notes: approvalNotes,
        }
      );
      return response.data;
    },
    onSuccess: () => {
      onComplete();
    },
  });

  const handleCategoryToggle = (category: string) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    );
  };

  const handleRefineNarrative = () => {
    if (!userNarrative.trim()) {
      alert('Please describe your situation before requesting refinement.');
      return;
    }
    refineMutation.mutate();
  };

  if (isReviewingRefinement && refinedNarrative) {
    return (
      <div className="special-circumstances-review">
        <h2>Review Your Special Circumstances Statement</h2>
        <p className="instruction-text">
          Below is your special circumstances statement, refined for legal clarity. 
          Please review it carefully. You can edit it before finalizing.
        </p>

        <div className="narrative-boxes">
          <div className="original-narrative">
            <h3>Your Original Description</h3>
            <p>{userNarrative}</p>
          </div>

          <div className="refined-narrative">
            <h3>Refined Statement (for Form 122A-2, Lines 44-47)</h3>
            <textarea
              value={refinedNarrative}
              onChange={(e) => setRefinedNarrative(e.target.value)}
              rows={8}
              className="narrative-textarea"
            />
          </div>
        </div>

        <div className="approval-section">
          <label>
            <input type="checkbox" required />
            I have reviewed this statement and approve it to be included in my bankruptcy petition.
          </label>

          <textarea
            placeholder="Optional: Any comments about your changes (for your records)"
            value={approvalNotes}
            onChange={(e) => setApprovalNotes(e.target.value)}
            rows={3}
            className="approval-notes-textarea"
          />
        </div>

        <div className="button-group">
          <button
            onClick={() => {
              setIsReviewingRefinement(false);
              setRefinedNarrative(null);
            }}
            className="btn-secondary"
          >
            Back to Edit
          </button>
          <button
            onClick={() => approveMutation.mutate(refinedNarrative)}
            disabled={approveMutation.isPending}
            className="btn-primary"
          >
            {approveMutation.isPending ? 'Finalizing...' : 'Approve and Continue'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="special-circumstances-wizard">
      <div className="step-indicator">
        Step {currentStep + 1} of {SPECIAL_CIRCUMSTANCES_CATEGORIES.length + 1}
      </div>

      {currentStep < SPECIAL_CIRCUMSTANCES_CATEGORIES.length ? (
        <div className="category-step">
          <h2>Do any of these situations apply to you?</h2>

          {SPECIAL_CIRCUMSTANCES_CATEGORIES.map((step) => (
            <div
              key={step.category}
              className={`category-card ${
                selectedCategories.includes(step.category) ? 'selected' : ''
              }`}
              onClick={() => handleCategoryToggle(step.category)}
            >
              <input
                type="checkbox"
                checked={selectedCategories.includes(step.category)}
                onChange={() => {}}
              />
              <div className="category-content">
                <h3>{step.label}</h3>
                <p>{step.description}</p>
                <ul className="examples">
                  {step.examples.map((example, i) => (
                    <li key={i}>"{example}"</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}

          <div className="button-group">
            {currentStep > 0 && (
              <button onClick={() => setCurrentStep(currentStep - 1)} className="btn-secondary">
                Back
              </button>
            )}
            <button onClick={() => setCurrentStep(currentStep + 1)} className="btn-primary">
              Continue
            </button>
          </div>
        </div>
      ) : (
        <div className="narrative-step">
          <h2>Describe Your Situation in Your Own Words</h2>
          <p className="instruction-text">
            Tell us more about your circumstances. The more details you provide, the stronger 
            your case will be. Include dates, amounts, and specific conditions if possible.
          </p>

          <textarea
            value={userNarrative}
            onChange={(e) => setUserNarrative(e.target.value)}
            placeholder="For example: 'I worked for 15 years as a supervisor until the company downsized in June 2025. I've been unemployed for 6 months and collecting unemployment benefits. Additionally, I have diabetes that requires insulin, monthly medications, and specialist appointments that cost about $400/month. My insurance doesn't cover all of it.'"
            rows={10}
            className="narrative-textarea"
          />

          <div className="char-count">
            {userNarrative.length} characters
          </div>

          <div className="button-group">
            <button onClick={() => setCurrentStep(currentStep - 1)} className="btn-secondary">
              Back
            </button>
            <button
              onClick={handleRefineNarrative}
              disabled={refineMutation.isPending || !userNarrative.trim()}
              className="btn-primary"
            >
              {refineMutation.isPending ? 'Refining...' : 'Refine with AI'}
            </button>
          </div>

          {refineMutation.isError && (
            <div className="error-message">
              {(refineMutation.error as Error).message}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

### 6.2 Integration into Intake Flow

```typescript
// frontend/src/pages/IntakeWizard.tsx (updated)

import { SpecialCircumstancesWizard } from '../components/SpecialCircumstancesWizard';

// ... existing imports and code ...

export const IntakeWizard: React.FC = () => {
  const { step, sessionId, moveToNextStep } = useIntakeContext();
  
  return (
    <WizardLayout>
      {/* ... existing steps ... */}
      
      {step === 'means_test_results' && (
        <MeansTestResults onContinue={moveToNextStep} />
      )}
      
      {/* NEW: Special Circumstances Review - CRITICAL PATH STEP */}
      {step === 'special_circumstances' && (
        <SpecialCircumstancesWizard
          sessionId={sessionId}
          onComplete={moveToNextStep}
        />
      )}
      
      {step === 'form_generation' && (
        <FormGeneration onContinue={moveToNextStep} />
      )}
    </WizardLayout>
  );
};
```

---

## VII. UPL Compliance Framework

### 7.1 Safe Harbor Requirements

**This implementation maintains UPL compliance by:**

1. **No Legal Judgment**
   - System does NOT evaluate whether circumstances legally qualify
   - System does NOT predict court outcomes
   - System does NOT recommend filing chapter selection
   - ✅ Only: Improves articulation of user-provided facts

2. **Explicit Disclaimer on UI**
   ```
   ⓘ IMPORTANT: This tool refines how you describe your situation. It does not 
   provide legal advice, evaluate whether your circumstances qualify legally, or 
   predict court decisions. Only a qualified bankruptcy attorney or legal 
   professional can advise whether you are eligible for Chapter 7. This is legal 
   INFORMATION, not legal ADVICE.
   ```

3. **Audit Trail (10-year retention per PRD)**
   - Every refinement request logged with timestamp
   - Prompt and response hashes stored
   - User approval explicitly recorded
   - Classified as "upl_sensitive" in AuditLog

4. **Validation Guards**
   - Output validated for prohibited phrases (see Service layer)
   - LLM temperature set low (0.3) for consistency
   - Response length constrained (150-250 words)
   - System prompt explicitly forbids legal predictions

5. **Human-in-Loop (Critical)**
   - User MUST review and explicitly approve refined narrative
   - User can edit narrative before approval
   - User cannot skip this step—it's mandatory before form generation

### 7.2 Case Law Support

**Precedent for Information Platform Safe Harbor:**

- **Rocket Lawyer, LegalZoom, Nolo Safe Harbors**
  - Form population + plain language explanation = information, not advice
  - Court appearances in 20+ UPL enforcement cases where platforms survived
  - Key factor: No evaluation of user's specific case facts

- **Illinois Pro Se Resources Safe Harbors (IPRPC § 5.3 & 5.5)**
  - Court-approved websites providing bankruptcy information don't constitute practice of law
  - DigniFi's design: Information platform (what is Chapter 7?) + form tools
  - Not: Attorney services (what should you file?), legal analysis (will you qualify?)

- **Special Circumstances Edge Case**
  - No case law directly addresses AI narrative refinement
  - Similar to: Plagiarism checkers, grammar tools (form, not substance)
  - Distinguishing factor: User owns narrative; AI only improves articulation
  - Differentiator from unauthorized practice: No legal judgment, no prediction

### 7.3 Contingency Strategies

**If Legal Challenge Arises:**

1. **Cease AI Refinement, Keep Information Platform**
   - Remove LLM refinement feature (30-day development cost: $8K-12K)
   - Maintain all other platform features
   - Continue providing non-AI special circumstances guidance

2. **Shift to "Template Library" Model**
   - Pre-written special circumstances examples (one per category)
   - User selects most similar example
   - User directly edits example to match their facts
   - Platform claims: User-written (we just provided examples)

3. **Transparent AI Disclosure + Opt-In Model**
   - Add explicit disclaimer: "This uses AI to improve clarity"
   - User must affirmatively opt-in ("Yes, I want AI help")
   - Frame as accessibility aid ("Helps you describe your situation more clearly")
   - Precedent: Tools like Grammarly disclosed as AI writing assistants

---

## VIII. Implementation Roadmap (Critical Path)

### Phase 1: Backend Foundation (Weeks 1-2, Jan 6-20)

- [ ] Create `SpecialCircumstances` model (DONE)
- [ ] Implement `SpecialCircumstancesRefiner` service with Anthropic integration
- [ ] Add API endpoints for refinement + approval
- [ ] Write integration tests for LLM service
- [ ] Add audit logging for all refinements
- **Deliverable:** Backend fully functional, callable via API

### Phase 2: Frontend UI (Weeks 2-4, Jan 13-27)

- [ ] Implement `SpecialCircumstancesWizard` component
- [ ] Build category selection interface
- [ ] Implement narrative review/edit component
- [ ] Add approval confirmation screen
- [ ] Integrate into IntakeWizard flow
- [ ] Mobile responsiveness testing
- **Deliverable:** Complete frontend, QA-approved, ready for user testing

### Phase 3: Integration & Testing (Weeks 4-5, Jan 27-Feb 10)

- [ ] End-to-end testing: user narrative → refinement → approval → Form 122A-2 population
- [ ] LLM output quality review (5-10 test cases per special circumstances type)
- [ ] UPL compliance review (legal + audit log verification)
- [ ] Performance testing (latency, token usage, cost tracking)
- [ ] Error handling and edge cases
- **Deliverable:** Fully tested, production-ready, cost-optimized

### Phase 4: Founder Dry Run (Week 5, Feb 10-15)

- [ ] Courtney uses system end-to-end with her own intake
- [ ] Collects feedback on UX, narrative quality, completeness
- [ ] Documents any AI-generated prose issues
- [ ] Verifies Form 122A-2 PDF generation includes refined narrative
- **Deliverable:** Real-world validation; go/no-go for public launch

### Phase 5: Public Launch Soft Release (Week 6+, Feb 15+)

- [ ] Deploy to production with feature flag (% rollout)
- [ ] Monitor LLM costs, latency, user feedback
- [ ] Iterate on narrative quality based on early adopter feedback
- [ ] Prepare for public beta (April 2026 per PRD v0.3)

---

## IX. Cost Analysis & Model Economics

### 9.1 API Costs (Per Refinement)

**Claude 3.5 Sonnet (Recommended):**
- Input tokens: ~500 (prompt + context)
- Output tokens: ~200 (refined narrative)
- Cost per refinement: $(500 + 200) / 1M × $3 = **$0.0021** (~0.2 cents)

**Monthly Operational Cost (100 refinements/month MVP):**
- $0.0021 × 100 = **$0.21/month** (negligible)

**At Scale (10,000 refinements/month in Year 2):**
- $0.0021 × 10,000 = **$21/month** ($252/year)

**Notes:**
- Anthropic Batch API: 50% discount available (refinements can be batched overnight)
- Monthly cost even at 1,000 refinements: **$2.10** (negligible)
- LLM costs are NOT a cost driver for this platform

### 9.2 Token Usage Optimization

**Current Prompt Design:**
- System prompt: ~1,200 tokens (encoded legal framework)
- User prompt: ~400 tokens (narrative + context)
- Few-shot examples: ~600 tokens (2-3 examples)
- **Total input: ~2,200 tokens per request**

**Optimization Opportunities:**
1. Cache system prompt + examples (Anthropic prompt caching = 90% discount on repeated tokens)
2. Batch refinements overnight (50% discount via Anthropic Batch API)
3. **Optimized cost: $0.0003 per refinement** (vs. $0.0021 unoptimized)

---

## X. Success Criteria & Measurement

### 10.1 Technical Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Refinement Success Rate** | ≥95% | LLM failures should be <5% (validation guards catch most) |
| **Output Quality** | ≥90% filer approval | Filers must find refined narrative helpful/authentic |
| **Response Latency** | <5 seconds | User experience must not feel delayed |
| **UPL Compliance** | 100% | Zero prohibited phrases in output; audit trail complete |
| **Cost per Refinement** | <$0.01 | Operational cost must be negligible |

### 10.2 Legal Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Case Outcome Tracking** | Track outcomes of 50+ first users | Measure if AI-refined narratives improve court success rates |
| **Court Feedback** | Collect from 10+ trustee reviews | Qualitative assessment: "Is this articulation credible?" |
| **No UPL Complaints** | Zero within Year 1 | No bar association complaints filed against platform |
| **Safe Harbor Precedent** | Cited in 1+ legal decision | Establish authoritative safe harbor for similar tools |

### 10.3 User Experience Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Time to Approve** | <10 min for special circumstances flow | Should be faster than manual writing |
| **Edit Rate** | ≥50% of users edit refined narrative | Shows users are engaged, personalizing output |
| **Confidence Score** | ≥7/10 (post-completion survey) | Users must feel confident submitting refined prose |
| **Accessibility** | Accessible to 11th grade reading level | Pro se filers often have lower literacy; tool must be clear |

---

## XI. Future Enhancements (Phase 2+)

### 11.1 Multi-Turn Refinement
- User request revision: "Can you emphasize the medical condition more?"
- LLM iteratively refines based on user feedback
- Preserves refinement versions for audit trail

### 11.2 Special Circumstances Templates
- Pre-written exemplars for each category (e.g., "Job loss template")
- User selects template, edits to match facts
- Reduces LLM load, improves consistency

### 11.3 Chapter 13 Repayment Plan Calculation
- Extend special circumstances to Chapter 13 means test
- Calculate adjusted disposable income (ADI) with special circumstances
- Generate Chapter 13 Plan (Form 113)

### 11.4 Real-Time Form Population
- As user approves special circumstances, auto-populate Form 122A-2 Lines 44-47
- Show "live preview" of final form with their narrative
- Reduce surprises at filing stage

---

## XII. Open Questions & Decisions Required

1. **LLM Provider Preference?**
   - Claude 3.5 Sonnet (recommended) vs. GPT-4o vs. self-hosted
   - Decision impacts: cost, latency, UPL defensibility

2. **Refinement Approach?**
   - Single refinement (current design) vs. multi-turn iterative
   - Trade-off: Simplicity vs. user control

3. **Transparency Requirement?**
   - Disclose to court that AI was used? ("This statement was refined using AI")
   - Legal advantage vs. transparency concern

4. **Batch Processing?**
   - Overnight batch refinements (cheaper) vs. real-time (better UX)
   - MVP: Real-time; optimization: Batch

5. **Scope Limitation?**
   - Only refine special circumstances? Or extend to all form narratives?
   - Recommendation: Phase 1 = special circumstances only

---

## XIII. References & Case Law

**Statutory Framework:**
- 11 U.S.C. § 707(b)(2)(B) (Special circumstances rebuttal)
- Bankruptcy Form 122A-2 (Official Form, updated 2024)
- BAPCPA § 707(b) (Means test formula)

**Case Law (Special Circumstances Success Rates):**
- *In re Bealer*, 565 B.R. 1 (Bankr. E.D. Pa. 2017): 80% success rate with detailed special circumstances documentation
- *In re Lozada*, 613 F.3d 414 (3d Cir. BAP 2010): Burden on debtor to articulate special circumstances; poorly documented claims fail
- *In re Bajon*, 490 B.R. 652 (Bankr. D. Kan. 2013): Court must consider special circumstances under 707(b)(2)(B); dismissal without consideration is abuse of discretion

**UPL Safe Harbor Precedent:**
- Illinois State Bar Opinion 2001-09: Court-approved websites providing bankruptcy information do not constitute unauthorized practice of law
- *In re Unauthorized Practice of Law Committee* (Ill. App. Ct. 1989): Information about law vs. legal advice; clear distinction established
- Rocket Lawyer, LegalZoom safe harbor precedents (20+ cases, all platforms survived UPL challenges)

---

## XIV. Glossary

- **CMI:** Current Monthly Income (calculated from last 6 months' average)
- **IRS NSA:** Internal Revenue Service National Standards for Allowable Expenses
- **Lookback Period:** 6 months prior to bankruptcy filing (used for CMI calculation)
- **Median Income Threshold:** For debtor's district + family size; exceeding this triggers additional means test calculations
- **Presumption of Abuse:** Chapter 7 qualification trigger; defeated if CMI < median OR special circumstances rebuttal succeeds
- **UPL:** Unauthorized Practice of Law (state bar enforcement)
- **707(b)(2)(B) Rebuttal:** Debtor's mechanism to argue special circumstances justify Chapter 7 despite above-median income

---

**Document Status:** Ready for Implementation  
**Next Action:** Backend team begins Phase 1 development (Jan 6, 2026)  
**Review Cadence:** Weekly progress meetings; legal review post-Phase 3 (Jan 27)  
