import {
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
} from 'react-aria-components'

/**
 * One labelled choice from a fixed list -- React Aria's Select, which gives it
 * the listbox semantics and keyboard handling a native `<select>` styled to
 * match would not. Shared by Settings and the approval inbox's filters.
 */
export default function Choice({
  label,
  options,
  selected,
  onChange,
}: {
  label: string
  options: { id: string; name: string }[]
  selected: string
  onChange: (id: string) => void
}) {
  return (
    <Select selectedKey={selected} onSelectionChange={(key) => onChange(String(key))}>
      <Label>{label}</Label>
      <Button>
        <SelectValue />
      </Button>
      <Popover>
        <ListBox items={options}>{(item) => <ListBoxItem id={item.id}>{item.name}</ListBoxItem>}</ListBox>
      </Popover>
    </Select>
  )
}
