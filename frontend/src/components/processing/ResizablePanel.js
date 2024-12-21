import React, { useState, useCallback, useEffect } from 'react';
import { Box, Flex } from '@chakra-ui/react';

export const ResizablePanel = ({ children, minWidth = 300, maxWidth = 800 }) => {
  const [width, setWidth] = useState(384);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback((e) => {
    setIsResizing(true);
    e.preventDefault();
  }, []);

  const stopResizing = useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = useCallback(
    (e) => {
      if (isResizing) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth >= minWidth && newWidth <= maxWidth) {
          setWidth(newWidth);
        }
      }
    },
    [isResizing, minWidth, maxWidth]
  );

  useEffect(() => {
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [resize, stopResizing]);

  return (
    <Flex w={`${width}px`} position="relative" h="100%">
      <Box
        position="absolute"
        left="-2px"
        top="0"
        w="4px"
        h="100%"
        cursor="col-resize"
        onMouseDown={startResizing}
        _hover={{ bg: 'blue.200' }}
        transition="background 0.2s"
        bg={isResizing ? 'blue.400' : 'transparent'}
      />
      {children}
    </Flex>
  );
};