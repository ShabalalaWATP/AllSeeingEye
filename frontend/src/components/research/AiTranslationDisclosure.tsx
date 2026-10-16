import type { TextTransformation } from '@/lib/api/sourceProvenance';
import { AiDisclosure } from './AiDisclosure';

/** A machine translation with recorded model identity or the application's LLM method. */
export function isAiTranslation(value: TextTransformation): boolean {
  return (
    value.kind === 'translation' &&
    value.origin === 'machine' &&
    (value.method === 'ase-title-translation-v1' || Boolean(value.model))
  );
}

/** Do not attribute an English title to AI without matching execution provenance. */
export function AiTranslationDisclosure({
  item,
  className = 'ml-2 inline-block text-2xs leading-5 text-muted',
}: {
  item: {
    title: string;
    title_en?: string | null | undefined;
    transformations?: readonly TextTransformation[] | undefined;
  };
  className?: string | undefined;
}) {
  if (
    !item.title_en ||
    !item.transformations?.some(
      (value) =>
        isAiTranslation(value) &&
        value.field === 'title' &&
        value.original_text === item.title &&
        value.transformed_text === item.title_en,
    )
  )
    return null;
  return <AiDisclosure kind="translation" compact className={className} />;
}
