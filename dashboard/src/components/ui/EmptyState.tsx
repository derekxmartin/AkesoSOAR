import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface Props {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  actionUrl?: string;
}

export default function EmptyState({ icon, title, description, actionLabel, actionUrl }: Props) {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="text-fg4 mb-3">{icon}</div>}
      <h3 className="text-lg font-semibold text-fg mb-1">{title}</h3>
      <p className="text-fg3 text-sm max-w-md mb-4">{description}</p>
      {actionLabel && actionUrl && (
        <button
          onClick={() => navigate(actionUrl)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
        >
          <Plus size={16} /> {actionLabel}
        </button>
      )}
    </div>
  );
}
