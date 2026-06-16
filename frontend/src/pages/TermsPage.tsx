/**
 * Terms of Service - plain-language draft.
 *
 * DRAFT — pending review by a licensed attorney before launch. The copy here is
 * deliberately UPL-safe (DigniFi provides legal information, not legal advice)
 * and avoids promising any data-handling behavior the platform does not yet
 * implement (e.g. a specific deletion window).
 */

import { Link } from 'react-router-dom';

export function TermsPage() {
  return (
    <main className="legal-page" id="main-content">
      <div className="legal-page-content">
        <p className="legal-eyebrow">
          <Link to="/" className="auth-link">
            ← Back to DigniFi
          </Link>
        </p>

        <h1>Terms of Service</h1>
        <p className="legal-updated">Last updated: June 12, 2026</p>

        <div className="info-box" role="note">
          <p>
            <strong>Draft.</strong> These terms are a working draft and are still being reviewed by
            a licensed attorney. They are provided so you can see how DigniFi works. They are not
            final.
          </p>
        </div>

        <section>
          <h2>1. What DigniFi is — and is not</h2>
          <p>
            DigniFi helps you understand the bankruptcy process and fill out official court forms in
            plain language. DigniFi gives you legal <em>information</em>. It does not give you legal{' '}
            <em>advice</em>.
          </p>
          <p>
            Using DigniFi does not make us your lawyers. It does not create an attorney–client
            relationship. We cannot tell you whether you should file, which chapter to file, or what
            is best for your specific situation. For advice about your case, please talk to a lawyer
            or your local legal aid office.
          </p>
        </section>

        <section>
          <h2>2. Who can use DigniFi</h2>
          <p>
            You must be at least 18 years old and filing on your own behalf. DigniFi is built for
            people in the United States who are representing themselves (filing “pro se”).
          </p>
        </section>

        <section>
          <h2>3. Your responsibilities</h2>
          <p>
            You are responsible for the information you enter and for the forms you file with the
            court. Please enter accurate, complete, and honest information. Bankruptcy forms are
            signed under penalty of perjury. Review every form carefully before you file it.
          </p>
        </section>

        <section>
          <h2>4. No guarantee of outcome</h2>
          <p>
            DigniFi cannot guarantee that your case will be accepted, that a fee will be waived, or
            that your debts will be discharged. A court makes those decisions. Any eligibility
            estimate we show is an estimate based on what you entered — not a promise.
          </p>
        </section>

        <section>
          <h2>5. Your information and privacy</h2>
          <p>
            We take your privacy seriously. Personal information you provide is encrypted. We use it
            to generate your forms and to show you eligibility information — not to sell to anyone.
            You may ask us to delete your information. If our data-retention practices change, we
            will update these terms to describe them clearly.
          </p>
        </section>

        <section>
          <h2>6. Acceptable use</h2>
          <p>
            Please use DigniFi only for your own bankruptcy preparation and follow the law. Do not
            misuse the service, attempt to disrupt it, or use it to harm others.
          </p>
        </section>

        <section>
          <h2>7. Disclaimers and limits</h2>
          <p>
            DigniFi is provided “as is,” without warranties of any kind. To the extent the law
            allows, DigniFi and its team are not liable for losses arising from your use of the
            service. Court rules and official forms change; we work to keep content current but
            cannot guarantee it is complete or error-free at all times.
          </p>
        </section>

        <section>
          <h2>8. Changes to these terms</h2>
          <p>
            We may update these terms as DigniFi grows. When we make a meaningful change, we will
            update the “Last updated” date above. Continuing to use DigniFi after a change means you
            accept the updated terms.
          </p>
        </section>

        <section>
          <h2>9. Contact</h2>
          <p>
            Questions about these terms? Reach us at{' '}
            <a className="auth-link" href="mailto:hello@dignifi.org">
              hello@dignifi.org
            </a>
            .
          </p>
        </section>

        <p className="legal-footer-note">
          This page provides general legal information, not legal advice.
        </p>
      </div>
    </main>
  );
}

export default TermsPage;
