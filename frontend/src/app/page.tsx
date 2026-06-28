import SiteHeader from "@/components/site-header";
import SiteFooter from "@/components/site-footer";
import HeroSection from "@/components/hero-section";
import PainPoints from "@/components/pain-points";
import Services from "@/components/services";
import MethodSection from "@/components/method-section";
import AgentBench from "@/components/agent-bench";
import Assurance from "@/components/assurance";
import ContactForm from "@/components/contact-form";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main id="top">
        <HeroSection />
        <PainPoints />
        <Services />
        <MethodSection />
        <AgentBench />
        <Assurance />
        <ContactForm />
      </main>
      <SiteFooter />
    </>
  );
}
