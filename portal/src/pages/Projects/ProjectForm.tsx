import type { FormEvent } from "react";
import Button from "../../ui/Button/Button";
import Card from "../../ui/Card/Card";
import StatusPill from "../../ui/StatusPill/StatusPill";

export interface ProjectFormProps {
  projectId: string;
  onProjectIdChange: (v: string) => void;
  name: string;
  onNameChange: (v: string) => void;
  feedstockOptions: string[];
  selectedFeedstock: string;
  onFeedstockChange: (v: string) => void;
  clientTarget: string;
  onClientTargetChange: (v: string) => void;
  submitting: boolean;
  formMsg: { text: string; ok: boolean } | null;
  onSubmit: (e: FormEvent) => void;
}

/** Presentational-only: the "Register project" form section. All state and
 * submit logic live in the Projects page; this just renders the markup. */
export default function ProjectForm({
  projectId,
  onProjectIdChange,
  name,
  onNameChange,
  feedstockOptions,
  selectedFeedstock,
  onFeedstockChange,
  clientTarget,
  onClientTargetChange,
  submitting,
  formMsg,
  onSubmit,
}: ProjectFormProps) {
  return (
    <Card as="form" style={{ marginBottom: "var(--space-5)" }} onSubmit={onSubmit}>
      <span className="micro">Register project</span>
      <div className="filters" style={{ marginTop: "var(--space-3)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <label className="micro" htmlFor="project-id-input">
            Project ID
          </label>
          <input
            id="project-id-input"
            aria-label="Project ID"
            value={projectId}
            onChange={(e) => onProjectIdChange(e.target.value)}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <label className="micro" htmlFor="project-name-input">
            Name
          </label>
          <input
            id="project-name-input"
            aria-label="Project name"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <label className="micro" htmlFor="project-feedstock-select">
            Feedstock
          </label>
          <select
            id="project-feedstock-select"
            aria-label="Feedstock"
            value={selectedFeedstock}
            disabled={feedstockOptions.length === 0}
            onChange={(e) => onFeedstockChange(e.target.value)}
          >
            <option value="">
              {feedstockOptions.length === 0
                ? "-- Create a registry config first --"
                : "-- Select feedstock --"}
            </option>
            {feedstockOptions.map((species) => (
              <option key={species} value={species}>
                {species}
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <label className="micro" htmlFor="project-client-target-input">
            Client Target (Optional)
          </label>
          <input
            id="project-client-target-input"
            aria-label="Client Target"
            type="number"
            min={0}
            step={1}
            value={clientTarget}
            placeholder="e.g. 25"
            onChange={(e) => onClientTargetChange(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={submitting} style={{ alignSelf: "flex-end" }}>
          Save
        </Button>
      </div>
      {formMsg && (
        <div style={{ marginTop: "var(--space-3)" }}>
          <StatusPill status={formMsg.ok ? "success" : "error"}>{formMsg.text}</StatusPill>
        </div>
      )}
    </Card>
  );
}
