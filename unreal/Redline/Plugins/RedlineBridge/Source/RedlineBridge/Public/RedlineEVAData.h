#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Presentation records only. Return-field, consumables and SEP decisions stay in ROS/core. */
struct REDLINEBRIDGE_API FRedlineFieldTile
{
    int32 Width=0, Height=0;
    FVector Origin=FVector::ZeroVector;
    double Resolution=0, Scale=0, Offset=0;
    uint8 Nodata=255;
    TArray<uint8> Pixels;
    static bool Parse(const TSharedPtr<FJsonObject>& Json,FRedlineFieldTile& Out,FString& Error);
    bool Sample(FVector MapPoint,double& Value) const;
};

struct REDLINEBRIDGE_API FRedlineEVALine
{
    TArray<TArray<FVector>> Abort, Terminate;
    FString LimitingCrew;
    double MarginMinutes=0;
    bool bHasMargin=false;
    static bool Parse(const TSharedPtr<FJsonObject>& Json,FRedlineEVALine& Out,FString& Error);
};

struct REDLINEBRIDGE_API FRedlineEVACrew
{
    FVector Position=FVector::ZeroVector;
    double OxygenKg=0, WaterKg=0, BatteryWh=0;
    static bool Parse(const TSharedPtr<FJsonObject>& Json,FRedlineEVACrew& Out,FString& Error);
};

struct REDLINEBRIDGE_API FRedlineEVADose
{
    double RateB=0, BackgroundB=0;
    double RateE=0, BackgroundE=0;
    FString Detector=TEXT("B");
    int32 SourceSol=0;
    FString SourceFile;
    bool bAlert=false;
    FString AlarmText(bool bFresh) const;
    static bool Parse(const TSharedPtr<FJsonObject>& Json,FRedlineEVADose& Out,FString& Error);
};
