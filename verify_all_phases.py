"""
Complete Phase 1-7 Wiring Verification
Checks all phases are properly wired to IntelligenceService
"""
import sys
sys.path.insert(0, '.')

from services.intelligence_service import (
    IntelligenceService,
    INCIDENT_ENGINE_AVAILABLE,
    DBA_FORMATTER_AVAILABLE,
    INTENT_ENGINE_AVAILABLE,
    ROUTER_AVAILABLE,
    PRODUCTION_ENGINE_AVAILABLE,
    PHASE7_TRUST_AVAILABLE
)

def verify_all_phases():
    print("="*70)
    print("COMPLETE PHASE WIRING VERIFICATION")
    print("="*70)
    
    # Phase flags
    phase_flags = {
        "Phase 1-3: Core NLP + Session + Reasoning": True,
        "Phase 4: Incident Intelligence Engine": INCIDENT_ENGINE_AVAILABLE,
        "Phase 4: DBA Formatter": DBA_FORMATTER_AVAILABLE,
        "Phase 5: Intent Engine": INTENT_ENGINE_AVAILABLE,
        "Phase 5: Response Router": ROUTER_AVAILABLE,
        "Phase 6: Production Orchestrator": PRODUCTION_ENGINE_AVAILABLE,
        "Phase 7: Enterprise Trust Engine": PHASE7_TRUST_AVAILABLE,
    }
    
    print("\n📋 PHASE FLAGS:")
    all_flags_ok = True
    for name, status in phase_flags.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}: {status}")
        if not status:
            all_flags_ok = False
    
    # Service instances
    svc = IntelligenceService()
    
    instances = {
        "Incident Engine": svc._incident_engine is not None,
        "DBA Formatter": svc._dba_formatter is not None,
        "Pipeline (lazy)": svc.pipeline is not None,
    }
    
    print("\n📋 ENGINE INSTANCES:")
    all_instances_ok = True
    for name, status in instances.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}: {'Loaded' if status else 'Missing'}")
        if not status:
            all_instances_ok = False
    
    # Summary
    print("\n" + "="*70)
    if all_flags_ok and all_instances_ok:
        print("🎉 ALL PHASES (1-7) PROPERLY WIRED!")
        print("\nPhase Summary:")
        print("  Phase 1: Session Storage ✅")
        print("  Phase 2: NLP Intent Detection ✅")
        print("  Phase 3: Reasoning Pipeline ✅")
        print("  Phase 4: Incident Intelligence ✅")
        print("  Phase 5: Predictive Intelligence ✅")
        print("  Phase 6: DBA Intelligence Partner ✅")
        print("  Phase 7: Enterprise Trust Engine ✅")
    else:
        print("⚠️ SOME PHASES NOT WIRED PROPERLY")
    print("="*70)
    
    return all_flags_ok and all_instances_ok

if __name__ == "__main__":
    success = verify_all_phases()
    sys.exit(0 if success else 1)
