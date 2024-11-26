import React from 'react';
import {
    Box,
    Stepper,
    Step,
    StepIndicator,
    StepStatus,
    StepIcon,
    StepNumber,
    StepTitle,
    StepDescription,
    StepSeparator,
    useBreakpointValue,
} from '@chakra-ui/react';

const StageNavigation = ({ stages, currentStage, onStageSelect }) => {
    const orientation = useBreakpointValue({ base: 'vertical', md: 'horizontal' });

    return (
        <Box width="100%" py={4}>
            <Stepper
                index={currentStage}
                orientation={orientation}
                gap={{ base: '0', md: '4' }}
            >
                {stages.map((stage, index) => (
                    <Step key={stage.id} onClick={() => onStageSelect(index)}>
                        <StepIndicator>
                            <StepStatus
                                complete={<StepIcon />}
                                incomplete={<StepNumber />}
                                active={<StepNumber />}
                            />
                        </StepIndicator>

                        <Box flexShrink='0'>
                            <StepTitle>{stage.name}</StepTitle>
                            {stage.description && (
                                <StepDescription>{stage.description}</StepDescription>
                            )}
                        </Box>

                        <StepSeparator />
                    </Step>
                ))}
            </Stepper>
        </Box>
    );
};

export default StageNavigation;