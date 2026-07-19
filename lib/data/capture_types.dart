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
  // smoke_0 / smoke_50 / smoke_90 / smoke_100 are produced dynamically by the
  // pyrolysis smoke-stage flow and are already stamped there.
}
