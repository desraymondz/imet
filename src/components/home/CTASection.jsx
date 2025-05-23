import Link from 'next/link';

export default function CTASection() {
    return (
        <section className="bg-[var(--color-primary-7)] py-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center">
                    <h2 className="text-3xl font-extrabold text-white">
                        Start building your network today
                    </h2>
                    <p className="mt-4 text-xl text-[var(--color-primary-1)]">
                        Never forget a name, face, or important detail again
                    </p>
                </div>
            </div>
        </section>
    );
}