<?xml version="1.0" encoding="UTF-8"?>
<!-- Driver that supplies the two EXPath File functions imageSummary.xsl uses.
     Saxon-PE/EE (what xslt2pe runs) has them built in; Saxon-HE does not.
     imageSummary.xsl itself is imported unmodified. -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:file="http://expath.org/ns/file"
  exclude-result-prefixes="xs file"
  version="3.0">

<xsl:import href="file:///home/user/ubl-work-on-svg-images/imageSummary.xsl"/>

<!-- accept either a native path or a file: URI, as EXPath implementations do -->
<xsl:function name="file:as-uri" as="xs:string">
  <xsl:param name="p" as="xs:string"/>
  <xsl:sequence select="if (starts-with($p, 'file:/')) then $p
                        else if (starts-with($p, '/'))  then 'file://' || $p
                        else string(resolve-uri($p, static-base-uri()))"/>
</xsl:function>

<xsl:function name="file:exists" as="xs:boolean">
  <xsl:param name="p" as="xs:string"/>
  <xsl:sequence select="unparsed-text-available(file:as-uri($p))"/>
</xsl:function>

<xsl:function name="file:list" as="xs:string*">
  <xsl:param name="dir" as="xs:string"/>
  <xsl:variable name="d" as="xs:string" select="file:as-uri($dir)"/>
  <xsl:sequence select="uri-collection(
                          (if (ends-with($d, '/')) then $d else $d || '/') ||
                          '?select=*;recurse=no;on-error=ignore')
                        ! replace(string(.), '^.*/', '')"/>
</xsl:function>

</xsl:stylesheet>
