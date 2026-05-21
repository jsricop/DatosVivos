type Props = { items: string[] };

export function Caveats({ items }: Props) {
  if (items.length === 0) return null;
  return (
    <aside
      role="note"
      aria-label="Advertencias"
      className="border-l-2 border-accent-2 pl-4 py-3 mt-4 text-ink-2"
    >
      <span className="text-kicker block mb-2">Advertencias</span>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="font-sans text-body-sm leading-[1.55]">
            {item}
          </li>
        ))}
      </ul>
    </aside>
  );
}
