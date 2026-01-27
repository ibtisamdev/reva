'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Save } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { ColorPicker } from '@/components/widget/color-picker';
import { WidgetPreview } from '@/components/widget/widget-preview';
import { EmbedCode } from '@/components/widget/embed-code';
import {
  getStoreSettings,
  updateStoreSettings,
  storeKeys,
  defaultWidgetSettings,
} from '@/lib/api/stores';
import type { WidgetSettings } from '@/lib/api/types';
import { useRequiredStoreId } from '@/lib/store-context';

export default function WidgetSettingsPage() {
  const queryClient = useQueryClient();
  const storeId = useRequiredStoreId();

  const { data: settings, isLoading } = useQuery({
    queryKey: storeKeys.settings(storeId),
    queryFn: () => getStoreSettings(storeId),
  });

  // Local state for form
  const [formData, setFormData] = useState<WidgetSettings>(
    defaultWidgetSettings.widget
  );

  // Sync form data when settings load
  useEffect(() => {
    if (settings?.widget) {
      setFormData(settings.widget);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateStoreSettings(storeId, { widget: formData }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: storeKeys.settings(storeId),
      });
      toast.success('Widget settings saved');
    },
    onError: () => {
      toast.error('Failed to save settings');
    },
  });

  const handleSave = () => {
    updateMutation.mutate();
  };

  const updateField = <K extends keyof WidgetSettings>(
    field: K,
    value: WidgetSettings[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[400px]" />
          <Skeleton className="h-[400px]" />
        </div>
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Settings Form */}
        <Card>
          <CardHeader>
            <CardTitle>Widget Appearance</CardTitle>
            <CardDescription>
              Customize how your support widget looks on your store.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <ColorPicker
              label="Primary Color"
              value={formData.primary_color}
              onChange={(value) => updateField('primary_color', value)}
            />

            <div className="space-y-2">
              <Label htmlFor="agent-name">Agent Name</Label>
              <Input
                id="agent-name"
                value={formData.agent_name}
                onChange={(e) => updateField('agent_name', e.target.value)}
                placeholder="Reva Support"
              />
              <p className="text-xs text-muted-foreground">
                This name appears in the widget header.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="welcome-message">Welcome Message</Label>
              <Textarea
                id="welcome-message"
                value={formData.welcome_message}
                onChange={(e) => updateField('welcome_message', e.target.value)}
                placeholder="Hi! How can I help you today?"
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                The first message customers see when they open the widget.
              </p>
            </div>

            <div className="space-y-3">
              <Label>Widget Position</Label>
              <RadioGroup
                value={formData.position}
                onValueChange={(value) =>
                  updateField('position', value as 'bottom-right' | 'bottom-left')
                }
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="bottom-right" id="bottom-right" />
                  <Label htmlFor="bottom-right" className="font-normal">
                    Bottom Right
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="bottom-left" id="bottom-left" />
                  <Label htmlFor="bottom-left" className="font-normal">
                    Bottom Left
                  </Label>
                </div>
              </RadioGroup>
            </div>

            <Button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="w-full"
            >
              {updateMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Preview */}
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
            <CardDescription>
              See how your widget will look on your store.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <WidgetPreview settings={formData} />
          </CardContent>
        </Card>
      </div>

      {/* Embed Code */}
      <EmbedCode storeId={storeId} />
    </div>
  );
}
