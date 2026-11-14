# CellState.msg — proje.md section 5
uint32 ix
uint32 iy
uint8 UNOBSERVED=0
uint8 DETECTED=1
uint8 NOT_DETECTED_LIMITED=2
uint8 state
float32 elevation_m
float32 slope_deg
float32 slope_sigma_deg
float32 rock_density_per_m2        # N(>=D*) per m^2
float32 speed_factor                # 0..1, insan hız çarpanı
uint8 provenance_status            # Provenance.status
string evidence_id
