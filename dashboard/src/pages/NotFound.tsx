import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import usePageTitle from "../hooks/usePageTitle";

export default function NotFound() {
  usePageTitle("404 Not Found");
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="text-7xl font-bold text-fg4 mb-2">404</div>
      <h1 className="text-xl font-semibold text-fg mb-2">Page not found</h1>
      <p className="text-fg3 text-sm mb-6 max-w-md">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <button
        onClick={() => navigate("/")}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
      >
        <ArrowLeft size={16} /> Back to Dashboard
      </button>
    </div>
  );
}
