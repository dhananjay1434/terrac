/// The single source of truth for evidence capture-type labels. Every media
/// row enqueued for /media upload MUST use one of these — the backend stores
/// it verbatim and the verifier portal groups evidence by it. Adding a new
/// evidence kind = one entry here, consumed everywhere.
class CaptureType {
  static const batchPhoto = 'batch_photo';
  static const flameCurtain = 'flame_curtain';
  static const quenching = 'quenching';
  static const flameHeight = 'flame_height';
  static const postBurnMass = 'post_burn_mass';
  static const packaging = 'packaging';
  static const endUse = 'end_use';
  static const labCertificate = 'lab_certificate';
  // V8 Part 4 (O) — video evidence. Uploaded through the same /api/v1/media
  // channel as photos (capture_type is a free-form validated string
  // server-side, and MultipartFile.fromPath infers video/mp4 from the
  // extension), so no backend change was needed to add these.
  static const quenchingVideo = 'quenching_video';
  static const densityVideo = 'density_video';
  // Deferred R1 — farmer + dispatch media (entity-scoped, via /api/v1/media
  // with X-Subject-Type/X-Subject-UUID instead of X-Batch-UUID).
  static const farmerSignature = 'farmer_signature';
  static const farmerIdDocument = 'farmer_id_document';
  static const fpicConsentPdf = 'fpic_consent_pdf';
  static const fpicHoldingPhoto = 'fpic_holding_photo';
  static const dispatchTruckPhoto = 'dispatch_truck_photo';
  static const dispatchInvoicePhoto = 'dispatch_invoice_photo';
  static const dispatchWeighTicket = 'dispatch_weigh_ticket';
  // PR-5 — day-start audit evidence (entity-scoped, subjectType
  // 'day_start_audit'). Facility photo is required; walkthrough video optional.
  static const dayStartFacilityPhoto = 'day_start_facility_photo';
  static const dayStartWalkthroughVideo = 'day_start_walkthrough_video';
  // smoke_0 / smoke_50 / smoke_90 / smoke_100 are produced dynamically by the
  // pyrolysis smoke-stage flow and are already stamped there.
}
