import { LegalLayout, Section } from "@/components/LegalLayout";

export const metadata = {
  title: "Privacy Policy — Elite Advance Data Services",
};

const CONTACT = "andy1gext2@gmail.com";

export default function PrivacyPage() {
  return (
    <LegalLayout title="Privacy Policy" updated="July 19, 2026">
      <p>
        This Privacy Policy explains how Elite Advance Data Services (&quot;Elite
        Advance,&quot; &quot;we,&quot; &quot;us&quot;) collects, uses, and shares
        information when you use our AI marketing, social media, and reputation
        management platform (the &quot;Service&quot;). By using the Service you
        agree to this Policy.
      </p>

      <Section heading="Information we collect">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Account information</strong> — your name, email address, and
            password (stored only as a secure one-way hash).
          </li>
          <li>
            <strong>Business profile</strong> — the business details you provide
            (industry, website, brand voice, goals, products, and uploaded media)
            so the AI can create on-brand content for you.
          </li>
          <li>
            <strong>Content you generate</strong> — posts, captions, images,
            videos, campaigns, and review responses created through the Service.
          </li>
          <li>
            <strong>Connected social accounts</strong> — when you link an account
            (e.g. Facebook, Instagram, Google, LinkedIn, X), we receive an access
            token and basic account/page information needed to schedule, publish,
            and read engagement on your behalf. Access tokens are{" "}
            <strong>encrypted at rest</strong> and are never shown or shared.
          </li>
          <li>
            <strong>Usage and billing data</strong> — how you use the Service,
            AI/image/video usage for quota and billing, and subscription status.
          </li>
        </ul>
      </Section>

      <Section heading="How we use information">
        <ul className="list-disc space-y-1 pl-5">
          <li>Provide, operate, and improve the Service.</li>
          <li>Generate content and recommendations tailored to your brand.</li>
          <li>
            Schedule and publish content to the social accounts you connect, and
            report analytics and reviews back to you.
          </li>
          <li>Process subscriptions and enforce plan limits.</li>
          <li>Secure the Service, prevent abuse, and comply with law.</li>
        </ul>
        <p>
          We do <strong>not</strong> sell your personal information, and we do not
          use data obtained through platform APIs (such as Meta) for advertising
          or for any purpose other than providing the Service to you.
        </p>
      </Section>

      <Section heading="Platform data (Meta and other integrations)">
        <p>
          When you connect a Facebook Page or Instagram account, we use Meta&apos;s
          APIs solely to perform the actions you request — publishing content you
          approve and reading engagement metrics for your own accounts — under the
          permissions you grant during connection. We store only the encrypted
          access token and the identifiers needed for those actions. You can
          revoke our access at any time (see &quot;Your choices&quot; and our{" "}
          <a href="/data-deletion" className="text-brand hover:underline">Data Deletion</a>{" "}
          instructions), after which we stop accessing the platform and delete the
          stored token.
        </p>
      </Section>

      <Section heading="Service providers we share with">
        <p>
          We share information only with vendors that help us run the Service,
          under agreements that limit their use of it:
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>AI providers</strong> (e.g. Anthropic, Google) to generate content, images, and video.</li>
          <li><strong>Social platforms</strong> (e.g. Meta/Facebook/Instagram, Google, LinkedIn, X) to publish and read your connected accounts.</li>
          <li><strong>Payments</strong> (Stripe) to process subscriptions.</li>
          <li><strong>Email</strong> (Resend) to send transactional messages such as password resets.</li>
          <li><strong>Hosting/infrastructure</strong> (Railway, Vercel) to run the application and store data.</li>
        </ul>
      </Section>

      <Section heading="Data retention and deletion">
        <p>
          We keep your information for as long as your account is active. You can
          delete a business (which removes its content, schedules, reviews,
          products, and connected accounts) from your dashboard, or delete your
          entire account by contacting us. See our{" "}
          <a href="/data-deletion" className="text-brand hover:underline">Data Deletion</a>{" "}
          page for full instructions. We honor deletion requests within 30 days,
          except where retention is required by law.
        </p>
      </Section>

      <Section heading="Security">
        <p>
          We use industry-standard measures to protect your data, including
          encryption in transit (HTTPS), encryption at rest for connected-account
          tokens, and hashed passwords. No method of transmission or storage is
          100% secure, but we work to protect your information.
        </p>
      </Section>

      <Section heading="Your choices">
        <ul className="list-disc space-y-1 pl-5">
          <li>Disconnect any social account from the Service at any time.</li>
          <li>Revoke our access from the platform itself (e.g. Facebook → Settings → Apps and Websites).</li>
          <li>Access, correct, or delete your data by contacting us.</li>
        </ul>
      </Section>

      <Section heading="Children">
        <p>
          The Service is intended for businesses and users 18 and older. We do not
          knowingly collect personal information from children.
        </p>
      </Section>

      <Section heading="Changes to this Policy">
        <p>
          We may update this Policy from time to time. Material changes will be
          reflected by the &quot;Last updated&quot; date above.
        </p>
      </Section>

      <Section heading="Contact">
        <p>
          Questions or requests? Email us at{" "}
          <a href={`mailto:${CONTACT}`} className="text-brand hover:underline">{CONTACT}</a>.
        </p>
      </Section>
    </LegalLayout>
  );
}
