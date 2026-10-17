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
 *
 * An option's `indent` nests it visually under the one before it (a category
 * under its parent); typing a letter still finds it by its name.
 *
 * Nothing chosen shows `placeholder`, in the client's language rather than
 * React Aria's default, which follows the browser's ("Element wählen").
 */
export default function Choice({
  label,
  options,
  selected,
  onChange,
  placeholder = 'Choose…',
  pulldown = false,
  labelHidden = false,
}: {
  label: string
  options: { id: string; name: string; indent?: number }[]
  selected: string
  onChange: (id: string) => void
  placeholder?: string
  /** A list's filter (task-372): the label sits inside the control ("Action All"),
   * still the control's accessible name. */
  pulldown?: boolean
  /** The label is said, not shown: a card's title already names the choice (task-372). */
  labelHidden?: boolean
}) {
  return (
    <Select
      className={pulldown ? 'react-aria-Select pulldown' : undefined}
      selectedKey={selected}
      onSelectionChange={(key) => onChange(String(key))}
      placeholder={placeholder}
    >
      <Label className={pulldown || labelHidden ? 'sr-only' : undefined}>{label}</Label>
      <Button>
        {pulldown && (
          <span className="pd-label" aria-hidden="true">
            {label}
          </span>
        )}
        <SelectValue />
      </Button>
      <Popover>
        <ListBox items={options}>
          {(item) => (
            <ListBoxItem
              id={item.id}
              textValue={item.name}
              style={item.indent ? { paddingInlineStart: `${0.5 + item.indent * 1.25}em` } : undefined}
            >
              {item.name}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </Select>
  )
}
