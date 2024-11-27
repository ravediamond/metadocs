import React from 'react';
import { 
  Box, 
  Flex, 
  Text, 
  Menu, 
  MenuButton, 
  MenuList, 
  MenuItem, 
  Button, 
  Progress 
} from '@chakra-ui/react';
import { ChevronDown } from 'lucide-react';
import { stages } from '../../constants/stages';

const StageNavigation = ({ currentStage, onStageChange, activeVersion }) => {
  return (
    <>
      <Menu>
        <MenuButton
          as={Button}
          rightIcon={<ChevronDown size={16} />}
          variant="ghost"
          bg="blue.50"
          color="blue.600"
          _hover={{ bg: 'blue.100' }}
        >
          <Flex align="center" gap={2}>
            <Text>{stages.find(s => s.id === currentStage)?.icon}</Text>
            <Text>{stages.find(s => s.id === currentStage)?.name} Stage</Text>
          </Flex>
        </MenuButton>
        <MenuList>
          {stages.map(stage => (
            <MenuItem
              key={stage.id}
              onClick={() => onStageChange(stage.id)}
              isDisabled={!activeVersion && stage.id !== 'new-version'}
              opacity={!activeVersion && stage.id !== 'new-version' ? 0.5 : 1}
            >
              <Flex align="center" gap={2}>
                <Text>{stage.icon}</Text>
                <Text>{stage.name}</Text>
              </Flex>
            </MenuItem>
          ))}
        </MenuList>
      </Menu>

      <Progress
        value={(stages.findIndex(s => s.id === currentStage) + 1) * (100 / stages.length)}
        size="xs"
        colorScheme="blue"
        borderRadius="full"
      />
      
      <Flex gap={2} mt={2}>
        {stages.map(stage => (
          <Box key={stage.id} flex={1}>
            <Text fontSize="xs" color="gray.500" textAlign="center">
              {stage.name}
            </Text>
          </Box>
        ))}
      </Flex>
    </>
  );
};

export default StageNavigation;