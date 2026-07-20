import { LegalLayout, Section } from "@/components/LegalLayout";

export const metadata = {
  title: "Terms of Service — Elite Advance Data Services",
};

const CONTACT = "andy1gext2@gmail.com";

export default function TermsPage() {
  return (
    <LegalLayout title="Terms of Service" updated="July 19, 2026">
      <p>
        These Terms of Service (&quot;Terms&quot;) govern your use of the Elite
        Advance Data Services platform (the &quot;Service&quot;). By creating an
        account or using the Service, you agree to these Terms.
      </p>

      <Section heading="The Service">
        <p>
          Elite Advance provides AI-assisted marketing tools, including content
          generation, scheduling and publishing to social platforms you connect,
          reputation management, and analytics. Features and limits vary by
          subscription plan.
        </p>
      </Section>

      <Section heading="Your account">
        <p>
          You are responsible for keeping your login credentials secure and for
          all activity under your account. You must provide accurate information
          and be at least 18 years old.
        </p>
      </Section>

      <Section heading="Connected accounts and platform rules">
        <p>
          When you connect a third-party account (such as Facebook or Instagram),
          you authorize us to act on your behalf within the permissions you grant.
          You are responsible for complying with each platform&apos;s own terms and
          policies, and you represent that you have the right to publish the
          content you create through the Service.
        </p>
      </Section>

      <Section heading="AI-generated content">
        <p>
          The Service uses AI to generate content and recommendations. AI output
          may be inaccurate or unsuitable — you are responsible for reviewing and
          approving all content before it is published. We do not guarantee any
          particular marketing result.
        </p>
      </Section>

      <Section heading="Acceptable use">
        <p>You agree not to use the Service to:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Publish unlawful, deceptive, infringing, or abusive content.</li>
          <li>Send spam or violate a platform&apos;s policies.</li>
          <li>Reverse engineer, disrupt, or gain unauthorized access to the Service.</li>
        </ul>
      </Section>

      <Section heading="Subscriptions and billing">
        <p>
          Paid plans are billed in advance on a recurring basis through our payment
          processor. Plan quotas (including AI, image, and video limits) apply as
          described at checkout. You can cancel at any time; fees already paid are
          non-refundable except where required by law.
        </p>
      </Section>

      <Section heading="Termination">
        <p>
          You may stop using the Service and delete your account at any time. We
          may suspend or terminate access for violations of these Terms or to
          protect the Service and its users.
        </p>
      </Section>

      <Section heading="Disclaimers and limitation of liability">
        <p>
          The Service is provided &quot;as is&quot; without warranties of any kind.
          To the maximum extent permitted by law, Elite Advance is not liable for
          indirect, incidental, or consequential damages, and our total liability
          is limited to the amount you paid for the Service in the 12 months before
          the claim.
        </p>
      </Section>

      <Section heading="Changes">
        <p>
          We may update these Terms from time to time. Continued use after changes
          means you accept the updated Terms.
        </p>
      </Section>

      <Section heading="Contact">
        <p>
          Questions about these Terms? Email{" "}
          <a href={`mailto:${CONTACT}`} className="text-brand hover:underline">{CONTACT}</a>.
        </p>
      </Section>
    </LegalLayout>
  );
}
