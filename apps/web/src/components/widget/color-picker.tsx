'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';

interface ColorPickerProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

// Preset colors based on design system
const presetColors = [
  '#0d9488', // Teal (primary)
  '#f97316', // Coral (accent)
  '#3b82f6', // Blue
  '#8b5cf6', // Purple
  '#ec4899', // Pink
  '#10b981', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#6b7280', // Gray
  '#1f2937', // Dark
];

export function ColorPicker({ value, onChange, label }: ColorPickerProps) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    // Only update if valid hex color
    if (/^#[0-9A-Fa-f]{6}$/.test(newValue)) {
      onChange(newValue);
    }
  };

  const handlePresetClick = (color: string) => {
    setInputValue(color);
    onChange(color);
    setOpen(false);
  };

  return (
    <div className="space-y-2">
      {label && <Label>{label}</Label>}
      <div className="flex gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className="w-10 h-10 p-0 border-2"
              style={{ backgroundColor: value }}
            >
              <span className="sr-only">Pick a color</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64" align="start">
            <div className="space-y-3">
              <div className="grid grid-cols-5 gap-2">
                {presetColors.map((color) => (
                  <button
                    key={color}
                    className={cn(
                      'h-8 w-8 rounded-md border-2 transition-transform hover:scale-110',
                      value === color
                        ? 'border-foreground'
                        : 'border-transparent'
                    )}
                    style={{ backgroundColor: color }}
                    onClick={() => handlePresetClick(color)}
                  >
                    <span className="sr-only">{color}</span>
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={value}
                  onChange={(e) => handlePresetClick(e.target.value)}
                  className="w-10 h-10 p-1 cursor-pointer"
                />
                <span className="text-sm text-muted-foreground self-center">
                  Custom color
                </span>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        <Input
          value={inputValue}
          onChange={handleInputChange}
          placeholder="#0d9488"
          className="w-28 font-mono"
        />
      </div>
    </div>
  );
}
