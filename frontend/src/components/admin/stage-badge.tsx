import { stageLabels, type Stage } from "@/lib/admin-api";

export default function StageBadge({ stage }: { stage: Stage }) {
  return <span className={`stage-badge stage-${stage}`}>{stageLabels[stage]}</span>;
}
