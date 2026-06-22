# Product

## Register

product

## Users

People facing Chapter 7 bankruptcy in the Northern District of Illinois — often for the first time, under significant financial and emotional stress. They are self-represented filers (pro se) who may have limited legal literacy but are not unsophisticated. They arrive overwhelmed, sometimes ashamed, carrying the weight of a situation that feels like failure even when it's a legal right. Their primary task on any screen is "get through this step without making a mistake that costs me my case." Secondary task: understand what they're filling in and why.

## Product Purpose

DigniFi guides people through the Chapter 7 bankruptcy intake process: collecting personal, income, expense, asset, and debt information; running a means test; and generating the official court forms (AO templates) required for filing in ILND. It removes the friction and fear of pro se filing by using plain language, trauma-informed copy, and a step-by-step wizard. Success looks like: a complete, accurate packet of forms the filer can take to the courthouse themselves.

DigniFi provides legal _information_, never legal _advice_ (UPL constraint is non-negotiable and baked into every user-facing touchpoint).

## Brand Personality

**Dignified · Direct · Warm**

DigniFi speaks like a knowledgeable friend at the public library — not a lawyer, not a chatbot, not a bureaucrat. It addresses people by their situation without shaming them for it. It is calm under pressure (the user is already stressed), direct without being curt, and warm without being patronizing. The aesthetic carries this: civic weight, honest materials, no ornamentation that isn't earning its place.

## Anti-references

- **Legal-disclaimer aesthetic** (LegalZoom, Nolo, law firm marketing): dense fine print, alarm-red accents, corporate distance, "consult an attorney" anxiety at every turn. DigniFi should feel like it trusts the user.
- **Slick fintech dashboard** (Credit Karma, Mint): Silicon Valley optimism, gamified progress rings, gradient metric cards, "You're on track!" microcopy. DigniFi is not a growth product. The user's financial situation is not a streak to maintain.
- **Generic government portal** (uscourts.gov, PACER): institutional gray, link-heavy walls of text, zero visual hierarchy, designed for courthouse clerks not filers. DigniFi borrows civic _authority_ not civic _bureaucracy_.

## Design Principles

1. **Calm the room first.** Every screen should lower the user's heart rate, not raise it. White space, clear labels, and quiet colors do more than any reassuring copy.
2. **One thing at a time.** The wizard exists to serialize complexity. Each step should have one job and make it obvious what that job is.
3. **Earn every word.** Plain language is not simplicity — it's precision. Every label, helper text, and error message should be the minimum words needed to be unambiguous.
4. **Dignity by default.** Use "filer" not "debtor." Use "amounts owed" not "debt." Language shapes how people feel about themselves in the process.
5. **Civic gravity, not civic gray.** The New Deal Civic identity (pine + gold + square corners) carries institutional weight without institutional coldness. That contrast is intentional — lean into it.

## Accessibility & Inclusion

- WCAG 2.1 AA minimum, with most colors verified at 4.5:1+ (documented in `src/styles/tokens.css`)
- Trauma-informed: avoid alarm-red for non-errors; avoid language that implies the user is at fault
- Reduced motion: all animations must have `prefers-reduced-motion` alternatives
- Skip navigation implemented for keyboard users
- Plain language target: 6th–8th grade reading level (Flesch-Kincaid grade 7)
- Users may be on low-end devices or slow connections; performance is an accessibility concern
