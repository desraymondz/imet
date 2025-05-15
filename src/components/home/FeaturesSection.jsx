import Link from 'next/link';
import FeatureCard from './FeatureCard';

export default function FeaturesSection() {
    const features = [
        {
            icon: "M12 6v6m0 0v6m0-6h6m-6 0H6",
            title: "Capture Memories",
            description: "Integreate to LinkedIn, record voice notes, type descriptions, or upload photos of the people you meet"
        },
        {
            icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
            title: "AI-Powered Summaries",
            description: "Our Telegram Bot AI transforms your notes into structured summaries about each person"
        },
        {
            icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z",
            title: "Organize Connections",
            description: "Keep all your connections organized with searchable cards and detailed profiles"
        }
    ];

    return (
        <section className="py-16 bg-[var(--background)]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center mb-16">
                    <h2 className="text-3xl font-extrabold text-[var(--foreground)]">How IMET Works</h2>
                    <p className="mt-4 max-w-2xl mx-auto text-xl text-[var(--foreground)]">
                        Capture, organize, and remember everyone you meet
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
                    {features.map((feature, index) => (
                        <FeatureCard key={index} {...feature} />
                    ))}
                </div>
            </div>
        </section>
    );
}