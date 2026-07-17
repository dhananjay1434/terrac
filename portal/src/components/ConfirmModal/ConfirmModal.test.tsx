import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ConfirmModal from "./ConfirmModal";

function renderModal(onConfirm = vi.fn().mockResolvedValue(undefined)) {
  render(
    <ConfirmModal
      open
      onOpenChange={vi.fn()}
      title="Issue credit — permanent"
      previewRows={[{ label: "Credits", value: "1.23 tCO₂e", mono: true }]}
      warning="This is irreversible."
      confirmToken="ISSUE-abc123"
      confirmLabel="Issue permanently"
      danger
      onConfirm={onConfirm}
    />,
  );
  return onConfirm;
}

describe("ConfirmModal", () => {
  it("keeps confirm disabled until the exact token is typed", () => {
    renderModal();
    const btn = screen.getByRole("button", { name: "Issue permanently" });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "ISSUE-wrong" },
    });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "ISSUE-abc123" },
    });
    expect(btn).toBeEnabled();
  });

  it("calls onConfirm once on click", async () => {
    const onConfirm = renderModal();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "ISSUE-abc123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Issue permanently" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledOnce());
  });

  it("disables all inputs while onConfirm is pending", async () => {
    let resolve!: () => void;
    const onConfirm = vi.fn(
      () => new Promise<void>((r) => (resolve = r)),
    );
    renderModal(onConfirm);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "ISSUE-abc123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Issue permanently" }));
    expect(await screen.findByRole("button", { name: "Working…" })).toBeDisabled();
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    resolve();
    await waitFor(() =>
      expect(screen.getByRole("textbox")).toBeEnabled(),
    );
  });

  it("shows a mismatch hint for a wrong token and a match hint for the right one", () => {
    renderModal();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "ISSUE-wron" },
    });
    expect(screen.getByText("Doesn't match — type it exactly")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "ISSUE-abc123" },
    });
    expect(screen.getByText("✓ Matches")).toBeInTheDocument();
    expect(
      screen.queryByText("Doesn't match — type it exactly"),
    ).not.toBeInTheDocument();
  });

  it("trims surrounding whitespace before comparing the token", () => {
    renderModal();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "  ISSUE-abc123  " },
    });
    expect(screen.getByRole("button", { name: "Issue permanently" })).toBeEnabled();
    expect(screen.getByText("✓ Matches")).toBeInTheDocument();
  });

  it("offers a copy button for the confirmation token", () => {
    const writeText = vi.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    renderModal();
    fireEvent.click(
      screen.getByRole("button", { name: "Copy confirmation token" }),
    );
    expect(writeText).toHaveBeenCalledWith("ISSUE-abc123");
  });
});
