import MitreCoverageMap from "../components/MitreCoverageMap";
import usePageTitle from "../hooks/usePageTitle";

export default function MitreCoverage() {
  usePageTitle("MITRE Coverage");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">MITRE ATT&CK Coverage</h1>
      <MitreCoverageMap />
    </div>
  );
}
