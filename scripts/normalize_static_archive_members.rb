#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "set"

GLOBAL_HEADER = "!<arch>\n".b
MEMBER_HEADER_SIZE = 60
MEMBER_NAME_SIZE = 16
MAX_CLASSIC_NAME_SIZE = MEMBER_NAME_SIZE - 1

def parse_members(data, path)
  raise "#{path}: invalid archive header" unless data.start_with?(GLOBAL_HEADER)

  members = []
  offset = GLOBAL_HEADER.bytesize
  while offset < data.bytesize
    header = data.byteslice(offset, MEMBER_HEADER_SIZE)
    raise "#{path}: truncated member header" unless header&.bytesize == MEMBER_HEADER_SIZE
    raise "#{path}: invalid member header" unless header.byteslice(58, 2) == "`\n"

    raw_name = header.byteslice(0, MEMBER_NAME_SIZE).rstrip
    size = Integer(header.byteslice(48, 10).strip, 10)
    payload_offset = offset + MEMBER_HEADER_SIZE
    raise "#{path}: truncated payload" if payload_offset + size > data.bytesize
    if raw_name.start_with?("#1/")
      name_size = Integer(raw_name.delete_prefix("#1/"), 10)
      name = data.byteslice(payload_offset, name_size).sub(/\x00+\z/, "").rstrip
      format = :extended
      name_storage_size = name_size
    elsif raw_name == "/" || raw_name == "//"
      name, format, name_storage_size = raw_name, :special, 0
    else
      name, format, name_storage_size = raw_name.delete_suffix("/"), :classic, MAX_CLASSIC_NAME_SIZE
    end
    members << { header_offset: offset, payload_offset: payload_offset, name: name,
                 format: format, name_storage_size: name_storage_size }
    offset = payload_offset + size
    offset += 1 if offset.odd?
  end
  raise "#{path}: trailing archive bytes" unless offset == data.bytesize
  members
end

def unique_name(original, occurrence, maximum_size, used_names)
  extension = File.extname(original)
  stem = File.basename(original, extension)
  salt = occurrence
  loop do
    token = Digest::SHA256.hexdigest("#{original}:#{salt}")[0, 4]
    suffix = "_#{token}"
    stem_size = maximum_size - extension.bytesize - suffix.bytesize
    raise "Cannot normalize #{original}" unless stem_size.positive?
    candidate = "#{stem.byteslice(0, stem_size)}#{suffix}#{extension}"
    return candidate unless used_names.include?(candidate)
    salt += 1
  end
end

def normalize_archive(path)
  data = File.binread(path)
  objects = parse_members(data, path).select { |entry| entry[:name].end_with?(".o") }
  duplicates = objects.group_by { |entry| entry[:name] }.select { |_name, entries| entries.length > 1 }
  return 0 if duplicates.empty?
  used = Set.new(objects.map { |entry| entry[:name] })
  renamed = 0
  duplicates.sort.each do |original, entries|
    entries.each_with_index do |entry, index|
      replacement = unique_name(original, index + 1, entry[:name_storage_size], used)
      used << replacement
      if entry[:format] == :extended
        data[entry[:payload_offset], entry[:name_storage_size]] = replacement.b.ljust(entry[:name_storage_size], "\0")
      else
        data[entry[:header_offset], MEMBER_NAME_SIZE] = "#{replacement}/".ljust(MEMBER_NAME_SIZE, " ").b
      end
      renamed += 1
    end
  end
  temporary = "#{path}.normalize-#{Process.pid}"
  begin
    File.binwrite(temporary, data)
    File.chmod(File.stat(path).mode, temporary)
    File.rename(temporary, path)
  ensure
    File.delete(temporary) if File.exist?(temporary)
  end
  renamed
end

abort("Usage: normalize_static_archive_members.rb ARCHIVE [ARCHIVE ...]") if ARGV.empty?
ARGV.each { |path| puts "#{path}: normalized #{normalize_archive(path)} duplicate object members" }
