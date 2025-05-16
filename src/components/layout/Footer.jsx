export default function Footer() {
    return (
        <footer className="bg-gray-800 py-12 mt-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center text-gray-400">
                    <p>&copy; {new Date().getFullYear()} iMet. All rights reserved.</p>
                </div>
            </div>
        </footer>
    );
}