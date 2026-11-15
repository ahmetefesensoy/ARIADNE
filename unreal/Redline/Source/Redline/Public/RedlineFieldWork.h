#pragma once
#include "CoreMinimal.h"

/** SCENARIO manual preparation inputs. These do not execute ROS operations. */
enum class ERedlineFieldWorkButtons : uint8
{
    None=0,
    Left=1,
    Right=2,
    Interact=4
};
ENUM_CLASS_FLAGS(ERedlineFieldWorkButtons)

enum class ERedlineFieldWorkState : uint8 { Idle,Active,Prepared,Cancelled };

/** Input-gated field work, independent of actors, clocks, physics and ROS.
 * Holds accumulate across release; missing alignment/focus pauses them.
 * Begin cannot replace active or prepared work. Cancel permits a new attempt.
 * Prepared means only that manual preparation finished; ROS owns the actual
 * operation, its products, custody and campaign completion.
 */
struct REDLINE_API FRedlineFieldWork
{
public:
    bool Begin(const FString& InKind);
    void Tick(double DeltaSeconds,uint8 HeldButtons,bool bAligned,bool bFocused=true,bool bEPressed=false);
    void Tick(double DeltaSeconds,ERedlineFieldWorkButtons HeldButtons,bool bAligned,bool bFocused=true,bool bEPressed=false)
    {Tick(DeltaSeconds,uint8(HeldButtons),bAligned,bFocused,bEPressed);}
    void Cancel();
    ERedlineFieldWorkState State() const {return CurrentState;}
    bool IsActive() const {return CurrentState==ERedlineFieldWorkState::Active;}
    bool IsPrepared() const {return CurrentState==ERedlineFieldWorkState::Prepared;}
    /** Returns true once per prepared attempt. Repeated polling never re-dispatches. */
    bool ConsumePrepared();
    FString PhaseText() const;
    FString Prompt() const;
    double Progress() const;
    double StageProgress() const;
    int32 StageIndex() const {return Stage;}
    const FString& Kind() const {return WorkKind;}
private:
    ERedlineFieldWorkState CurrentState=ERedlineFieldWorkState::Idle;
    FString WorkKind;
    int32 Stage=0;
    double HeldSeconds=0;
    bool bInteractArmed=false,bPreparedConsumed=false,bLastAligned=false,bLastFocused=true;
    int32 StageCount() const;
    double HoldDuration() const;
    uint8 RequiredButton() const;
    bool IsConfirmation() const;
    void Advance();
};
