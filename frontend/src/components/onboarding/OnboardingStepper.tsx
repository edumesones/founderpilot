/**
 * Onboarding progress stepper component.
 */

"use client";

import { OnboardingStep } from "@/lib/api/onboarding";

interface OnboardingStepperProps {
  steps: OnboardingStep[];
  currentStep: number;
}

export function OnboardingStepper({ steps, currentStep }: OnboardingStepperProps) {
  return (
    <div className="w-full max-w-md mx-auto">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.step} className="flex items-center">
            {/* Step Circle */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center
                  border-2 transition-all duration-300
                  ${
                    step.completed
                      ? "bg-green-500 border-green-500 text-white"
                      : step.current
                      ? "bg-white border-blue-500 text-blue-500"
                      : "bg-gray-100 border-gray-300 text-gray-400"
                  }
                `}
              >
                {step.completed ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  <span className="font-medium">{index + 1}</span>
                )}
              </div>
              <span
                className={`
                  mt-2 text-sm font-medium
                  ${step.completed ? "text-green-600" : step.current ? "text-blue-600" : "text-gray-400"}
                `}
              >
                {step.name}
              </span>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div
                className={`
                  flex-1 h-0.5 mx-4
                  ${index < currentStep - 1 ? "bg-green-500" : "bg-gray-200"}
                `}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default OnboardingStepper;
