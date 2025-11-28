# Thesys Evaluation for Retention Reasoning Agent Frontend

## Executive Summary

**Recommendation**: Use Crayon (Thesys's open-source React components) for the frontend, but build our own backend reasoning engine instead of using their C1 API.

**Reasoning**: Crayon provides high-quality, MIT-licensed React components optimized for AI agent UIs, but the C1 API adds unnecessary vendor lock-in and costs for our use case.

---

## What is Thesys?

Thesys offers a "Generative UI" platform with two main components:

1. **C1 API** (Paid, Proprietary): OpenAI-compatible API that returns structured UI components instead of text
2. **Crayon SDK** (Free, MIT License): Open-source React components and state management for AI agent interfaces

### Key Architecture
```
User Input → C1 API → Structured UI Response → Crayon React SDK → Rendered UI
```

---

## Detailed Evaluation

### ✅ What We CAN Use

**Crayon React Components (MIT Licensed)**
- **Package**: `@crayonai/react-core` and `@crayonai/react-ui`
- **License**: MIT (permissive, commercial-friendly)
- **Components**: Pre-built UI components for:
  - Agent conversations
  - Streaming responses
  - Interactive charts/graphs
  - Forms and data displays
  - State management hooks
- **Tech Stack**: React + TypeScript + Radix UI + shadcn/ui patterns
- **Installation**: `npm install @crayonai/react-core`
- **GitHub**: https://github.com/thesysdev/crayon
- **Flexibility**: "Seamlessly integrates with any backend" per their docs

### ❌ What We Should NOT Use

**C1 API (Paid Service)**
- **Pricing**: $10 free credits, then pay-as-you-go (exact pricing unclear)
- **Lock-in**: Requires Thesys account and API key
- **Dependency**: Backend must route through their infrastructure
- **Overhead**: Adds latency (your backend → C1 API → response)
- **Control**: Limited customization of reasoning logic
- **Data**: Sends customer data to third-party service

---

## Limitations of Thesys Approach

### Technical Limitations
1. **Vendor Dependency**: C1 API is required for full Generative UI flow
2. **Latency**: Additional hop through Thesys infrastructure
3. **Customization**: Limited control over UI generation logic
4. **Design System**: Tied to Crayon/shadcn aesthetic (though extensible)
5. **Streaming Complexity**: State management during partial renders can be tricky

### Business Limitations
1. **Cost Opacity**: Usage-based pricing without clear rate card
2. **Data Privacy**: Customer retention data sent to third-party
3. **SLA Dependency**: Uptime relies on Thesys infrastructure
4. **Compliance**: May complicate GDPR/SOC2 requirements

---

## Recommended Approach: Hybrid Strategy

### Use Crayon Components (Frontend Only)
- Install open-source Crayon React libraries
- Use their pre-built components for:
  - Reasoning graph visualization
  - Hypothesis display
  - Streaming agent responses
  - Interactive causal diagrams
- Benefit from their WCAG-compliant, mobile-responsive design
- Full control over styling and theming

### Build Our Own Backend
- Keep all reasoning logic in our LangGraph pipeline
- Direct integration with our BigQuery feature store
- No third-party data sharing
- Complete control over causal inference algorithms
- Optimize for our specific retention use cases

### Architecture
```
User → Niti Frontend (Crayon Components) → Niti Backend (LangGraph) → BigQuery
                                        ↓
                                   Gemini/Claude
```

**No Thesys C1 API in the loop.**

---

## Build vs Buy Analysis

### If We Use Full Thesys Stack (C1 API + Crayon)

**Pros:**
- Fast initial setup (~1-2 weeks)
- Pre-built UI generation logic
- Maintained by Thesys team

**Cons:**
- Ongoing API costs (unclear pricing)
- Vendor lock-in
- Data privacy concerns
- Limited reasoning customization
- Latency overhead

**Estimated Effort**: 2 weeks integration

---

### If We Use Crayon Only + Build Backend ✅ (Recommended)

**Pros:**
- Full control over reasoning logic
- No ongoing API costs
- Zero vendor lock-in
- Better data privacy
- Optimized for our use case
- Still benefit from polished React components

**Cons:**
- More upfront development (~4-6 weeks)
- Need to maintain reasoning backend

**Estimated Effort**:
- **Backend Reasoning Agent**: 3-4 weeks
- **Crayon Integration**: 1-2 weeks
- **Total**: 4-6 weeks

**ROI**: Worth the investment for a core differentiator like retention reasoning.

---

### If We Build Everything From Scratch (No Thesys)

**Pros:**
- Maximum control
- Zero dependencies

**Cons:**
- Reinventing UI wheels
- 8-12 weeks of work
- Ongoing maintenance burden
- Accessibility/responsiveness work

**Estimated Effort**: 8-12 weeks (not recommended)

---

## Technical Implementation Plan

### Phase 1: Backend Reasoning Agent (3-4 weeks)
1. **Design causal reasoning framework** (1 week)
   - Hypothesis generation logic
   - Causal inference algorithms (Granger causality, DAGs, etc.)
   - Statistical validation framework

2. **Build LangGraph reasoning pipeline** (2 weeks)
   - Reasoning agent node
   - Hypothesis testing node
   - Evidence gathering node
   - Explanation generation node

3. **Integration with feature store** (1 week)
   - Query enriched_customers table
   - Statistical analysis on cohorts
   - Performance optimization

### Phase 2: Frontend with Crayon (1-2 weeks)
1. **Install and configure Crayon** (2-3 days)
   - Set up `@crayonai/react-core` and `@crayonai/react-ui`
   - Configure theming to match Niti brand
   - Set up streaming hooks

2. **Build reasoning UI components** (3-5 days)
   - Hypothesis cards
   - Causal graph visualization
   - Evidence display
   - Confidence indicators
   - Interactive exploration

3. **Connect to backend** (2-3 days)
   - WebSocket/SSE for streaming
   - State management
   - Error handling

### Phase 3: Testing & Refinement (1 week)
- User testing with marketers
- Performance optimization
- Edge case handling

---

## Answer to Key Questions

### Can we use Thesys?
**Yes, but only Crayon components (not C1 API).**

### What are the limitations?
- C1 API adds cost, latency, and vendor lock-in
- Crayon alone requires we build the reasoning backend
- Design system is opinionated (though extensible)

### Should we build or buy?
**Hybrid: Use Crayon (buy) + Build reasoning backend (build).**
- Best of both worlds
- 4-6 weeks vs 2 weeks (acceptable for core differentiator)
- Complete control over retention logic

### Can we reuse their React SDK?
**Yes! That's the recommended approach.**
- Crayon is MIT licensed and backend-agnostic
- Use their components with our LangGraph backend
- No need for C1 API

---

## Next Steps

1. ✅ **Start building Retention Reasoning Agent backend** (this PR)
2. Install Crayon packages in frontend repo
3. Design reasoning graph visualization UX
4. Connect Crayon components to our backend API
5. Iterate based on marketer feedback

---

## Conclusion

**Use Crayon components (open-source, MIT) for the frontend UI, but build our own retention reasoning backend in LangGraph.** This gives us:
- High-quality, accessible React components (saved 4-6 weeks of UI work)
- Full control over reasoning logic (our competitive moat)
- No vendor lock-in or recurring API costs
- Complete data privacy

The extra 2-4 weeks of backend development is justified for a core product differentiator like explainable retention AI.
