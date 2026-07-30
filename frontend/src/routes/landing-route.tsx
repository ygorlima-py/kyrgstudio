import { HeroSection } from '@/features/marketing/components/hero-section'
import { ProductPreview } from '@/features/marketing/components/product-preview'
import { HowItWorks } from '@/features/marketing/components/how-it-works'
import { FeatureGrid } from '@/features/marketing/components/feature-grid'
import { AudienceSection } from '@/features/marketing/components/audience-section'
import { FaqSection } from '@/features/marketing/components/faq-section'
import { CallToActionSection } from '@/features/marketing/components/call-to-action-section'

export function LandingRoute() {
  return (
    <>
      <HeroSection />
      <ProductPreview />
      <HowItWorks />
      <FeatureGrid />
      <AudienceSection />
      <FaqSection />
      <CallToActionSection />
    </>
  )
}
