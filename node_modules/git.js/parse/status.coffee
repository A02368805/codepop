_ = require 'underscore'
_.str = require 'underscore.string'

# parser of output in short format
parseShort = (out) ->
	return [] unless out
	lines = _.str.lines out
	lines.map (l) ->
		status = l.substr(0, 2)
		path = l.substr(2).trim()
		return {
		path: path
		status: fullStatus(status)
		}

fullStatus = (s) ->
	switch s.trim()
		when 'M' then 'modified'
		when 'A' then 'new'
		when 'AM' then 'new'
		when 'D' then 'deleted'
		when 'R' then 'renamed'
		when 'C' then 'copied'
		when 'U' then 'updated'
		else
			return ''

# normal output parser
parseFull = (out) ->
	return [] unless out

	lines = _.str.lines out
	lines = lines.map (l) ->
		_.str.ltrim(l, '#').trim()

	statuses = [
		['new file:', 'new'],
		['modified:', 'modified'],
		['removed:', 'deleted'],
		['deleted:', 'deleted']
	]

	# todo support untracked files

	files = lines.map (l) ->
		st = _.find statuses, (s) ->
			_.str(l).startsWith(s[0])
		if st
			path = l.substr(st[0].length).trim()
			return {path: path, status: st[1]}
		return null

	return files.filter (f) ->
		f?

# export status output parsers
module.exports = {
	short: parseShort
	full: parseFull
}
