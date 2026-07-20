import { LegalLayout, Section } from "@/components/LegalLayout";

export const metadata = {
  title: "Data Deletion — Elite Advance Data Services",
};

const CONTACT = "andy1gext2@gmail.com";

export default function DataDeletionPage() {
  return (
    <LegalLayout title="Data Deletion Instructions" updated="July 19, 2026">
      <p>
        You can delete the data Elite Advance Data Services holds about you at any
        time. This page explains how, including data obtained when you connect a
        Facebook or Instagram account.
      </p>

      <Section heading="Delete a business and its data">
        <p>
          Signed in to the app, open your dashboard, click the &quot;⋯&quot; menu
          on a business, and choose <strong>Delete</strong>. This permanently
          removes that business and everything in it — generated content,
          campaigns, schedules, reviews, products, and any connected social
          accounts (including stored access tokens).
        </p>
      </Section>

      <Section heading="Disconnect a connected account">
        <p>
          To stop Elite Advance from accessing a social account without deleting
          your whole business, remove the connection from the Schedule tab in the
          app. You can also revoke access directly on the platform — for Facebook
          and Instagram, go to{" "}
          <strong>Facebook → Settings &amp; Privacy → Settings → Apps and
          Websites</strong>, select Elite Advance Data Services, and remove it.
          Once revoked, we stop accessing the platform and delete the stored token.
        </p>
      </Section>

      <Section heading="Delete your entire account">
        <p>
          To delete your account and all associated personal data, email us at{" "}
          <a href={`mailto:${CONTACT}?subject=Data%20Deletion%20Request`} className="text-brand hover:underline">
            {CONTACT}
          </a>{" "}
          with the subject <strong>&quot;Data Deletion Request&quot;</strong> from
          the email address on your account. We will verify the request and delete
          your data within <strong>30 days</strong>, except where we are required
          to retain certain records by law.
        </p>
      </Section>

      <Section heading="What gets deleted">
        <ul className="list-disc space-y-1 pl-5">
          <li>Your account and profile information.</li>
          <li>Business profiles, products, and uploaded media.</li>
          <li>Generated content, campaigns, schedules, and analytics.</li>
          <li>Reviews synced into the Service and any AI responses.</li>
          <li>Connected-account access tokens.</li>
        </ul>
      </Section>

      <Section heading="Contact">
        <p>
          For any deletion question, email{" "}
          <a href={`mailto:${CONTACT}`} className="text-brand hover:underline">{CONTACT}</a>.
        </p>
      </Section>
    </LegalLayout>
  );
}
