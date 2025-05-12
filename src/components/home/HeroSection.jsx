import Link from 'next/link';

export default function HeroSection() {
    return (
        <section className="bg-[var(--color-secondary-1)] py-20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center">
                    <h1 className="text-4xl font-bold tracking-tight text-[var(--foreground)] sm:text-5xl md:text-6xl">
                        <span className="block">Never forget</span>
                        <span className="block text-[var(--color-secondary-6)]">who you meet</span>
                    </h1>
                    <p className="mt-3 max-w-md mx-auto text-base text-[var(--foreground)] sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
                        IMET helps you remember and organize the important people in your personal and professional life.
                    </p>
                    <div className="mt-10 flex justify-center gap-4 flex-wrap">
                        <Link
                            href="/memory-capture"
                            className="px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-[var(--color-secondary-6)] hover:bg-[var(--color-secondary-7)] md:text-lg"
                        >
                            Add a Memory
                        </Link>
                        <Link
                            href="/connections"
                            className="px-8 py-3 border border-transparent text-base font-medium rounded-md text-[var(--color-secondary-7)] bg-[var(--color-secondary-1)] hover:bg-[var(--color-secondary-2)] md:text-lg"
                        >
                            View Connections
                        </Link>
                        <Link
                            href="/nudges"
                            className="px-8 py-3 border border-transparent text-base font-medium rounded-md text-[var(--color-primary-7)] bg-[var(--color-primary-1)] hover:bg-[var(--color-primary-2)] md:text-lg"
                        >
                            Smart Nudges
                        </Link>
                    </div>
                </div>
            </div>
        </section>
    );
}