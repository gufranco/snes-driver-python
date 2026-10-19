local cpu = manager.machine.devices[":maincpu"]
local space = cpu.spaces["program"]
local state = cpu.state
local frames_wanted = tonumber(os.getenv("TRACE_FRAMES"))
local gap = tonumber(os.getenv("TRACE_GAP"))
local out_path = os.getenv("TRACE_OUT")
local schedule = os.getenv("TRACE_INPUT") or ""
local period, hold, names = schedule:match("^(%d+):(%d+):(.+)$")

trace = { taps = {}, held = {}, order = {}, pending = nil, frame = 0, pairs_gap = 0.0, apart = 1.0 }

local function registers()
  return string.format(
    "%06X %02X %d %02X %04X",
    state["PC"].value,
    state["P"].value,
    state["E"].value,
    state["DB"].value,
    state["D"].value
  )
end

local function tally(event, width)
  local key = string.format("%s %06X %d %s", event.direction, event.address, width, event.registers)
  local held = trace.held[key]
  if held == nil then
    held = { count = 0, first = trace.frame, index = event.index }
    trace.held[key] = held
    trace.order[#trace.order + 1] = key
  end
  held.count = held.count + 1
end

local function flush()
  if trace.pending ~= nil then
    tally(trace.pending, 1)
    trace.pending = nil
  end
end

local function heard(direction, offset)
  local event = {
    direction = direction,
    address = offset,
    pc = state["PC"].value,
    registers = registers(),
    index = string.format("%04X %04X", state["X"].value, state["Y"].value),
    time = manager.machine.time:as_double(),
  }
  local before = trace.pending
  if before ~= nil and before.direction == direction and before.pc == event.pc and before.address + 1 == offset then
    local apart = event.time - before.time
    if apart <= gap then
      if apart > trace.pairs_gap then
        trace.pairs_gap = apart
      end
      tally(before, 2)
      trace.pending = nil
      return
    end
    if apart < trace.apart then
      trace.apart = apart
    end
  end
  flush()
  trace.pending = event
end

for range in string.gmatch(os.getenv("TRACE_RANGES"), "[^;]+") do
  local low, high = range:match("^(%x+)-(%x+)$")
  local first, last = tonumber(low, 16), tonumber(high, 16)
  trace.taps[#trace.taps + 1] = space:install_write_tap(first, last, "w" .. low, function(offset, data, mask)
    heard("write", offset)
  end)
  trace.taps[#trace.taps + 1] = space:install_read_tap(first, last, "r" .. low, function(offset, data, mask)
    heard("read", offset)
  end)
end

local fields = {}
if names ~= nil then
  local port = manager.machine.ioport.ports[":ctrl1:joypad:JOYPAD"]
  for name in string.gmatch(names, "[^,]+") do
    fields[#fields + 1] = port.fields["P1 " .. name]
  end
end
trace.fields = fields

local function press()
  if #fields == 0 then
    return
  end
  local every, down = tonumber(period), tonumber(hold)
  local slot = (trace.frame // every) % #fields + 1
  local pressing = (trace.frame % every) < down
  for index, field in ipairs(fields) do
    field:set_value((index == slot and pressing) and 1 or 0)
  end
end

local function finish()
  flush()
  local handle = io.open(out_path, "w")
  handle:write(string.format("frames %d\n", trace.frame))
  handle:write(string.format("taps %d\n", #trace.taps))
  handle:write(string.format("widest-pair %.12f\n", trace.pairs_gap))
  handle:write(string.format("closest-apart %.12f\n", trace.apart))
  for _, key in ipairs(trace.order) do
    local held = trace.held[key]
    handle:write(string.format("access %s %s %d %d\n", key, held.index, held.count, held.first))
  end
  handle:close()
  manager.machine:exit()
end

trace.subscription = emu.register_frame_done(function()
  trace.frame = trace.frame + 1
  press()
  if trace.frame == frames_wanted then
    finish()
  end
end)
