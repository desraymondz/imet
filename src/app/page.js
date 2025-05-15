import HeroSection from '@/components/home/HeroSection';
import FeaturesSection from '@/components/home/FeaturesSection';
import CTASection from '@/components/home/CTASection';
import GoogleForm from '@/components/home/GoogleForm';
import Footer from '@/components/layout/Footer';

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen scroll-smooth">
      <HeroSection />
      <FeaturesSection />
      <CTASection />
      <GoogleForm />
      <Footer />
    </div>
  );
}