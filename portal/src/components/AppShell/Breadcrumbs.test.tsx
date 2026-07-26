import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Breadcrumbs from "./Breadcrumbs";

const CASES: [string, string][] = [
  ["/dashboard", "Dashboard"],
  ["/batches", "Batches"],
  ["/lab/scan", "Lab / Scan"],
  ["/registry", "Registry"],
  ["/projects", "Projects"],
  ["/farmers", "Farmers"],
  ["/dispatch", "Dispatch"],
];

describe("Breadcrumbs (audit S3)", () => {
  it.each(CASES)("shows %s label", (path, label) => {
    const { getByText } = render(
      <MemoryRouter initialEntries={[path]}>
        <Breadcrumbs />
      </MemoryRouter>,
    );
    expect(getByText(label)).toBeInTheDocument();
  });

  it("renders nothing on an unmapped route (/login)", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/login"]}>
        <Breadcrumbs />
      </MemoryRouter>,
    );
    expect(container.firstChild).toBeNull();
  });
});
