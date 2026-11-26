# Metadata derives from the authored HTML; article text and permanent URLs stay intact.
require 'cgi'

module GlossarySeoFilters
  def seo_excerpt(input, limit = 170)
    text = input.to_s.gsub(/<script\b[^>]*>.*?<\/script>/mi, '')
      .gsub(/<[^>]+>/, ' ')
    text = CGI.unescapeHTML(text).gsub(/[[:space:]\u00a0\u200b]+/, ' ').strip
    return text if text.length <= limit

    text[0, limit - 1].sub(/\s+\S*\z/, '').rstrip + '…'
  end

  def seo_images(input)
    input.to_s.scan(/<img\b[^>]*\bsrc=(["'])(.*?)\1/mi).filter_map do |_quote, src|
      # Article sources use literal relative_url expressions. Built HTML also works.
      path = src[/\{\{\s*['"]([^'"]+)['"]\s*\|\s*relative_url\s*\}\}/, 1] || src
      next unless path.start_with?('/') && !path.start_with?('//') && !path.include?('{{')

      site = @context.registers[:site]
      baseurl = site.baseurl.to_s.sub(%r{/$}, '')
      path = path.delete_prefix(baseurl) unless baseurl.empty?
      original = path.sub(%r{/thumbs/\d+x\d+/}, '/')
      File.file?(File.join(site.source, CGI.unescape(original))) ? original : path
    end.uniq
  end
end

Liquid::Template.register_filter(GlossarySeoFilters)
