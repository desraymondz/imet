export default function FeatureCard({ icon, title, description }) {
    return (
        <div className="bg-[var(--background)] rounded-lg p-6 shadow-sm">
            <div className="text-[var(--color-secondary-6)] mb-3">
                <svg className="h-10 w-10" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
                </svg>
            </div>
            <h3 className="text-xl font-medium text-[var(--foreground)]">{title}</h3>
            <p className="mt-2 text-base text-[var(--foreground)]">
                {description}
            </p>
        </div>
    );
}