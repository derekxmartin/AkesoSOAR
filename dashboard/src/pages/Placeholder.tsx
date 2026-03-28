export default function Placeholder({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{title}</h1>
      <p className="text-fg3">This page will be implemented in a future phase.</p>
    </div>
  );
}
